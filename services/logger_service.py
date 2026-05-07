from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

LOGGER_NAME = "student_reengagement_mvp"


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def configure_logging(logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = get_logger()
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    file_handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False


def init_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                phone TEXT NOT NULL,
                call_status TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def log_call_activity(
    database_path: Path,
    student_id: str,
    phone: str,
    call_status: str,
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO call_logs (student_id, phone, call_status, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (student_id, phone, call_status, timestamp),
        )
        connection.commit()
    finally:
        connection.close()