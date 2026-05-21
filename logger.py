import json
import sqlite3
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "agent_logs.jsonl"
METRICS_DB = LOG_DIR / "metrics.db"

RUN_ID = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
RUN_STARTED_AT = time.perf_counter()
RUN_METRICS: Dict[str, Any] = {
    "total_tokens": 0,
    "total_steps": 0,
    "total_errors": 0,
    "code_skills_executed": 0,
    "llm_calls": 0,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_storage() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(METRICS_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_metrics (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                total_tokens INTEGER NOT NULL,
                total_steps INTEGER NOT NULL,
                total_errors INTEGER NOT NULL,
                total_duration_seconds REAL NOT NULL,
                code_skills_executed INTEGER NOT NULL,
                llm_calls INTEGER NOT NULL
            )
            """
        )


def log_event(event_type: str, **data: Any) -> None:
    """Append a machine-parseable JSON event.

    JSONL logs make the agent observable without binding it to one logging
    vendor. Each line is a complete event that can be loaded by Streamlit,
    pandas, jq, or external SIEM tooling.
    """
    ensure_storage()
    record = {
        "timestamp": utc_now(),
        "run_id": RUN_ID,
        "event_type": event_type,
        **data,
    }
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def record_step() -> None:
    RUN_METRICS["total_steps"] += 1


def record_error() -> None:
    RUN_METRICS["total_errors"] += 1


def record_llm_tokens(prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    RUN_METRICS["llm_calls"] += 1
    RUN_METRICS["total_tokens"] += int(prompt_tokens or 0) + int(completion_tokens or 0)


def record_code_execution() -> None:
    RUN_METRICS["code_skills_executed"] += 1


def log_exception(exc: BaseException, context: Optional[Dict[str, Any]] = None) -> None:
    record_error()
    log_event(
        "error",
        exception=repr(exc),
        stack_trace=traceback.format_exc(),
        context=context or {},
    )


def finalize_run() -> None:
    ensure_storage()
    finished_at = utc_now()
    duration = time.perf_counter() - RUN_STARTED_AT
    with sqlite3.connect(METRICS_DB) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO run_metrics (
                run_id,
                started_at,
                finished_at,
                total_tokens,
                total_steps,
                total_errors,
                total_duration_seconds,
                code_skills_executed,
                llm_calls
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                RUN_ID,
                RUN_ID.split("-")[0],
                finished_at,
                RUN_METRICS["total_tokens"],
                RUN_METRICS["total_steps"],
                RUN_METRICS["total_errors"],
                duration,
                RUN_METRICS["code_skills_executed"],
                RUN_METRICS["llm_calls"],
            ),
        )
    log_event(
        "run_end",
        total_tokens=RUN_METRICS["total_tokens"],
        total_steps=RUN_METRICS["total_steps"],
        total_errors=RUN_METRICS["total_errors"],
        total_duration_seconds=duration,
        code_skills_executed=RUN_METRICS["code_skills_executed"],
        llm_calls=RUN_METRICS["llm_calls"],
    )
