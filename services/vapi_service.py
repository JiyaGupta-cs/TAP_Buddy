from __future__ import annotations

import os
from typing import Any

import requests

from .logger_service import get_logger
from .rabbitmq_service import publish_call_request

logger = get_logger()

DEFAULT_VAPI_URL = "https://api.vapi.ai/call"


def create_vapi_call(student: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("VAPI_API_KEY", "").strip()
    assistant_id = os.getenv("VAPI_ASSISTANT_ID", "").strip()
    phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID", "").strip()

    if not api_key:
        raise ValueError("Missing VAPI_API_KEY")
    if not assistant_id:
        raise ValueError("Missing VAPI_ASSISTANT_ID")
    if not phone_number_id:
        raise ValueError("Missing VAPI_PHONE_NUMBER_ID")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Correct VAPI payload format per API reference
    payload = {
        "assistantId": assistant_id,
        "phoneNumberId": phone_number_id,
        "customer": {
            "number": student["phone"],
        },
        "assistantOverrides": {
            "variableValues": {
                "student_name": student["name"],
                "course_name": student["course"],
                "days_inactive": str(student["days_inactive"]),
            }
        }
    }

    publish_call_request(student, payload)

    try:
        response = requests.post(DEFAULT_VAPI_URL, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        logger.error("VAPI request failed for %s: %s", student["name"], exc)
        return {
            "success": False,
            "error": str(exc),
        }

    if response.status_code not in (200, 201, 202):
        logger.error(
            "VAPI returned %s for %s: %s",
            response.status_code,
            student["name"],
            response.text,
        )
        return {
            "success": False,
            "status_code": response.status_code,
            "error": response.text,
        }

    try:
        response_data = response.json()
    except ValueError:
        logger.error("VAPI returned invalid JSON for %s", student["name"])
        return {
            "success": False,
            "status_code": response.status_code,
            "error": "VAPI returned invalid JSON",
        }

    logger.info("VAPI call succeeded for %s", student["name"])
    return {
        "success": True,
        "status_code": response.status_code,
        "data": response_data,
    }


def trigger_outbound_call(student: dict[str, Any]) -> dict[str, Any]:
    return create_vapi_call(student)