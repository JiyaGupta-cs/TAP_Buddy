from __future__ import annotations

import contextlib
import json
import os
from datetime import datetime, timezone
from typing import Any

try:
    import pika
except ImportError:  # pragma: no cover - optional dependency during local editing
    pika = None

from .logger_service import get_logger

logger = get_logger()

DEFAULT_RABBITMQ_URL = "amqp://guest:guest@localhost:5672/%2F"
DEFAULT_RABBITMQ_QUEUE = "student_call_requests"


def build_call_request_message(student: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "student": student,
        "vapi_payload": payload,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


def publish_call_request(student: dict[str, Any], payload: dict[str, Any]) -> bool:
    rabbitmq_url = os.getenv("RABBITMQ_URL", "").strip()
    queue_name = os.getenv("RABBITMQ_QUEUE", DEFAULT_RABBITMQ_QUEUE).strip() or DEFAULT_RABBITMQ_QUEUE

    if not rabbitmq_url:
        logger.info("RABBITMQ_URL not configured, skipping queue publish for %s", student["name"])
        return False

    if pika is None:
        logger.warning("pika is not installed, skipping RabbitMQ publish for %s", student["name"])
        return False

    connection = None
    try:
        connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(build_call_request_message(student, payload)).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
        logger.info("Queued call request for %s in RabbitMQ queue %s", student["name"], queue_name)
        return True
    except Exception as exc:
        logger.warning("RabbitMQ publish failed for %s: %s", student["name"], exc)
        return False
    finally:
        with contextlib.suppress(Exception):
            if connection is not None:
                connection.close()
