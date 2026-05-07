from __future__ import annotations

import os
from typing import Any

import requests

from .logger_service import get_logger

logger = get_logger()


def _extract_value(record: dict[str, Any], keys: list[str], default: Any = "") -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return default


def _map_frappe_student(record: dict[str, Any]) -> dict[str, Any] | None:
    student = {
        "student_id": _extract_value(record, ["student_id", "name", "id"]),
        "name": _extract_value(record, ["student_name", "full_name", "name"]),
        "phone": _extract_value(record, ["phone", "mobile_number", "contact_number", "mobile"]),
        "language": _extract_value(record, ["language", "preferred_language"], "English"),
        "course": _extract_value(record, ["course", "course_name", "program"]),
        "days_inactive": _extract_value(record, ["days_inactive", "inactive_days"], 0),
        "progress": _extract_value(record, ["progress", "completion", "course_progress"], 0),
        "pending_assignments": _extract_value(
            record,
            ["pending_assignments", "assignments_pending", "pending_tasks"],
            0,
        ),
    }

    if not student["student_id"] or not student["name"] or not student["phone"] or not student["course"]:
        return None

    return student


def fetch_students_from_frappe() -> list[dict[str, Any]]:
    frappe_url = os.getenv("FRAPPE_URL", "").strip()
    frappe_api_key = os.getenv("FRAPPE_API_KEY", "").strip()
    frappe_api_secret = os.getenv("FRAPPE_API_SECRET", "").strip()

    if not frappe_url or not frappe_api_key or not frappe_api_secret:
        logger.info("Frappe configuration not complete, skipping Frappe fetch")
        return []

    endpoint = frappe_url.rstrip("/") + "/api/resource/Student?limit_page_length=100"
    headers = {
        "Authorization": f"token {frappe_api_key}:{frappe_api_secret}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(endpoint, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.error("Frappe fetch failed: %s", exc)
        return []
    except ValueError as exc:
        logger.error("Frappe returned invalid JSON: %s", exc)
        return []

    records = payload.get("data", [])
    if not isinstance(records, list):
        logger.error("Unexpected Frappe response format")
        return []

    students: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        mapped_student = _map_frappe_student(record)
        if mapped_student:
            students.append(mapped_student)

    return students