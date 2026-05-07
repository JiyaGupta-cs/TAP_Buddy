from __future__ import annotations

from typing import Any

INACTIVE_THRESHOLD_DAYS = 5


def validate_student_record(student: Any) -> dict[str, Any] | None:
    if not isinstance(student, dict):
        return None

    required_fields = [
        "student_id",
        "name",
        "phone",
        "language",
        "course",
        "days_inactive",
        "progress",
        "pending_assignments",
    ]

    missing_fields = [field for field in required_fields if field not in student]
    if missing_fields:
        return None

    try:
        normalized_student = {
            "student_id": str(student["student_id"]).strip(),
            "name": str(student["name"]).strip(),
            "phone": str(student["phone"]).strip(),
            "language": str(student["language"]).strip(),
            "course": str(student["course"]).strip(),
            "days_inactive": int(student["days_inactive"]),
            "progress": student["progress"],
            "pending_assignments": int(student["pending_assignments"]),
        }
    except (TypeError, ValueError):
        return None

    if not normalized_student["student_id"] or not normalized_student["name"]:
        return None

    return normalized_student


def is_inactive_student(student: dict[str, Any]) -> bool:
    return int(student.get("days_inactive", 0)) >= INACTIVE_THRESHOLD_DAYS


def filter_inactive_students(students: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [student for student in students if is_inactive_student(student)]