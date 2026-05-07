from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .services.logger_service import get_logger, init_database, log_call_activity
from .services.nudging_engine import validate_student_record, filter_inactive_students
from .services.vapi_service import create_vapi_call

logger = get_logger()
BASE = Path(__file__).resolve().parent
ENV_FILE = BASE / ".env"
STUDENTS_FILE = BASE / "students.json"
DB_FILE = BASE / "database" / "calls.db"


def load_env(env_path: Path | None = None) -> None:
    path = env_path or ENV_FILE
    if not path.exists():
        logger.info("No .env file found at %s", path)
        return

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def load_students() -> list[dict[str, Any]]:
    if not STUDENTS_FILE.exists():
        logger.error("students.json not found: %s", STUDENTS_FILE)
        return []

    try:
        with STUDENTS_FILE.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        logger.error("Failed to read students.json: %s", exc)
        return []

    students: list[dict[str, Any]] = []
    if not isinstance(payload, list):
        logger.error("students.json must be an array")
        return []

    for item in payload:
        s = validate_student_record(item)
        if s:
            students.append(s)

    return students


def main() -> int:
    load_env()
    init_database(DB_FILE)

    students = load_students()
    inactive = filter_inactive_students(students)

    if not inactive:
        logger.info("No inactive students to call")
        print("No inactive students found")
        return 0

    for student in inactive:
        name = student.get("name")
        logger.info("Triggering call for %s", name)
        try:
            resp = create_vapi_call(student)
        except Exception as exc:
            logger.error("Exception while calling %s: %s", name, exc)
            log_call_activity(DB_FILE, str(student.get("student_id")), str(student.get("phone")), "failed")
            print({"student_id": student.get("student_id"), "name": name, "status": "failed", "error": str(exc)})
            continue

        status = "initiated" if resp.get("success") else "failed"
        log_call_activity(DB_FILE, str(student.get("student_id")), str(student.get("phone")), status)

        if resp.get("success"):
            logger.info("Call initiated for %s", name)
        else:
            logger.error("Failed to call %s: %s", name, resp.get("error"))

        print({"student_id": student.get("student_id"), "name": name, "status": status, "response": resp})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
