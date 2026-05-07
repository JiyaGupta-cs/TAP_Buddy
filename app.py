from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from .services.frappe_service import fetch_students_from_frappe
from .services.logger_service import (
    configure_logging,
    get_logger,
    init_database,
    log_call_activity,
)
from .services.nudging_engine import filter_inactive_students, validate_student_record
from .services.vapi_service import trigger_outbound_call

BASE_DIR = Path(__file__).resolve().parent
STUDENTS_FILE = BASE_DIR / "database" / "students.json"
DATABASE_FILE = BASE_DIR / "database" / "calls.db"
LOGS_DIR = BASE_DIR / "logs"

logger = get_logger()


def load_env_file(env_path: Path | None = None) -> None:
    env_file = env_path or (BASE_DIR / ".env")
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def read_students_from_json() -> list[dict[str, Any]]:
    if not STUDENTS_FILE.exists():
        logger.error("students.json not found at %s", STUDENTS_FILE)
        return []

    try:
        with STUDENTS_FILE.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in students.json: %s", exc)
        return []
    except Exception as exc:
        logger.error("Failed to read students.json: %s", exc)
        return []

    if not isinstance(payload, list):
        logger.error("students.json must contain a JSON array")
        return []

    valid_students: list[dict[str, Any]] = []
    for item in payload:
        student = validate_student_record(item)
        if student:
            valid_students.append(student)

    return valid_students


def load_students() -> tuple[list[dict[str, Any]], str]:
    frappe_students = fetch_students_from_frappe()
    if frappe_students:
        valid_students: list[dict[str, Any]] = []
        for item in frappe_students:
            student = validate_student_record(item)
            if student:
                valid_students.append(student)
        if valid_students:
            logger.info("Loaded %d students from Frappe", len(valid_students))
            return valid_students, "frappe"

    json_students = read_students_from_json()
    logger.info("Loaded %d students from JSON fallback", len(json_students))
    return json_students, "json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_env_file()
    configure_logging(LOGS_DIR)
    init_database(DATABASE_FILE)

    students, source = load_students()
    app.state.students = students
    app.state.students_source = source

    logger.info("Application initialized with %d students from %s", len(students), source)
    yield


app = FastAPI(
    title="AI-Powered Multilingual Student Re-engagement MVP",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root() -> dict[str, Any]:
    students = getattr(app.state, "students", [])
    source = getattr(app.state, "students_source", "unknown")
    inactive_students = filter_inactive_students(students)

    return {
        "status": "ok",
        "project": "AI-powered multilingual student re-engagement voice agent",
        "students_loaded": len(students),
        "inactive_students": len(inactive_students),
        "inactive_threshold_days": 5,
        "data_source": source,
    }


@app.get("/students")
def get_students() -> dict[str, Any]:
    students = getattr(app.state, "students", [])
    return {
        "count": len(students),
        "students": students,
    }


@app.get("/trigger-calls")
def trigger_calls() -> dict[str, Any]:
    students = getattr(app.state, "students", [])
    inactive_students = filter_inactive_students(students)

    if not inactive_students:
        return {
            "status": "success",
            "message": "No inactive students found for calling",
            "triggered": 0,
            "results": [],
        }

    results: list[dict[str, Any]] = []

    for student in inactive_students:
        student_name = student["name"]
        logger.info("Triggering call for %s", student_name)

        try:
            response = trigger_outbound_call(student)
            call_status = "initiated" if response.get("success") else "failed"

            log_call_activity(
                database_path=DATABASE_FILE,
                student_id=str(student["student_id"]),
                phone=str(student["phone"]),
                call_status=call_status,
            )

            if response.get("success"):
                logger.info("Call initiated for %s", student_name)
            else:
                logger.error("Failed to call student %s", student_name)

            results.append(
                {
                    "student_id": student["student_id"],
                    "name": student_name,
                    "phone": student["phone"],
                    "status": call_status,
                    "vapi_response": response,
                }
            )
        except Exception as exc:
            log_call_activity(
                database_path=DATABASE_FILE,
                student_id=str(student["student_id"]),
                phone=str(student["phone"]),
                call_status="failed",
            )
            logger.error("Failed to call student %s: %s", student_name, exc)

            results.append(
                {
                    "student_id": student["student_id"],
                    "name": student_name,
                    "phone": student["phone"],
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return {
        "status": "completed",
        "triggered": len(inactive_students),
        "results": results,
    }


@app.get("/health")
def health_check() -> dict[str, Any]:
    students = getattr(app.state, "students", [])
    env_status = {
        "VAPI_API_KEY": bool(os.getenv("VAPI_API_KEY")),
        "VAPI_ASSISTANT_ID": bool(os.getenv("VAPI_ASSISTANT_ID")),
        "VAPI_PHONE_NUMBER_ID": bool(os.getenv("VAPI_PHONE_NUMBER_ID")),
        "RABBITMQ_URL": bool(os.getenv("RABBITMQ_URL")),
        "RABBITMQ_QUEUE": bool(os.getenv("RABBITMQ_QUEUE")),
        "FRAPPE_URL": bool(os.getenv("FRAPPE_URL")),
        "FRAPPE_API_KEY": bool(os.getenv("FRAPPE_API_KEY")),
        "FRAPPE_API_SECRET": bool(os.getenv("FRAPPE_API_SECRET")),
    }

    return {
        "status": "healthy",
        "students_loaded": len(students),
        "database_ready": DATABASE_FILE.exists(),
        "env_status": env_status,
    }