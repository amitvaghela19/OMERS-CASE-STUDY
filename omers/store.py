"""SQLite storage and the logged read-only SQL runner."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB_PATH = DATA / "omers.db"
CLEAN_PATH = DATA / "cleaned_workbook.xlsx"
LOG_PATH = DATA / "sql_query_log.csv"

TABLES = ("hierarchy", "bs_by_region", "kpis", "equity_bridge")
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum|reindex|grant)\b",
    re.IGNORECASE,
)


def engine() -> Engine:
    DATA.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )


def db_ready() -> bool:
    if not DB_PATH.exists():
        return False
    with engine().connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'table'")
        ).fetchall()
    names = {row[0] for row in rows}
    return set(TABLES).issubset(names)


def ingest_frames(frames: dict[str, pd.DataFrame]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    eng = engine()
    with eng.begin() as conn:
        for name in TABLES:
            frames[name].to_sql(name, conn, if_exists="replace", index=False)
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS query_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    sql_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    row_count INTEGER,
                    error TEXT,
                    duration_ms REAL
                )
                """
            )
        )
    with pd.ExcelWriter(CLEAN_PATH) as writer:
        frames["hierarchy"].to_excel(writer, sheet_name="Hierarchy", index=False)
        frames["bs_by_region"].to_excel(writer, sheet_name="BS by Region", index=False)
        frames["kpis"].to_excel(writer, sheet_name="KPIs", index=False)
        frames["equity_bridge"].to_excel(writer, sheet_name="Equity Bridge", index=False)


def load_tables() -> dict[str, pd.DataFrame]:
    eng = engine()
    return {name: pd.read_sql(text(f"SELECT * FROM {name}"), eng) for name in TABLES}


def table_schema() -> list[dict[str, object]]:
    """Column names and types for the four cleaned tables, plus a row count."""
    overview: list[dict[str, object]] = []
    with engine().connect() as conn:
        for name in TABLES:
            info = conn.execute(text(f"PRAGMA table_info({name})")).fetchall()
            count = conn.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
            overview.append(
                {
                    "name": name,
                    "rows": int(count or 0),
                    "columns": [(row[1], row[2] or "TEXT") for row in info],
                }
            )
    return overview


def preview_table(name: str, limit: int = 5) -> pd.DataFrame:
    if name not in TABLES:
        raise ValueError("Unknown table.")
    with engine().connect() as conn:
        return pd.read_sql(
            text(f"SELECT * FROM {name} LIMIT :limit"),
            conn,
            params={"limit": limit},
        )


def validate_select(sql: str) -> str:
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("Enter a SELECT query.")
    if ";" in cleaned:
        raise ValueError("Only one statement is allowed.")
    if not re.match(r"(?is)^(select|with)\b", cleaned):
        raise ValueError("Only a SELECT query is allowed.")
    if FORBIDDEN.search(cleaned):
        raise ValueError("That statement is not allowed.")
    return cleaned


def _write_log(source: str, sql_text: str, status: str, row_count: int | None, error: str, duration_ms: float) -> None:
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    DATA.mkdir(parents=True, exist_ok=True)
    with engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO query_log
                    (created_at, source, sql_text, status, row_count, error, duration_ms)
                VALUES
                    (:created_at, :source, :sql_text, :status, :row_count, :error, :duration_ms)
                """
            ),
            {
                "created_at": created,
                "source": source,
                "sql_text": sql_text,
                "status": status,
                "row_count": row_count,
                "error": error,
                "duration_ms": round(duration_ms, 1),
            },
        )
    row = {
        "created_at": created,
        "source": source,
        "sql_text": sql_text,
        "status": status,
        "row_count": row_count,
        "error": error,
        "duration_ms": round(duration_ms, 1),
    }
    pd.DataFrame([row]).to_csv(LOG_PATH, mode="a", header=not LOG_PATH.exists(), index=False)


def run_select(sql: str, params: dict | None = None, source: str = "sql_tab") -> pd.DataFrame:
    started = time.perf_counter()
    try:
        cleaned = validate_select(sql)
        with engine().connect() as conn:
            if params:
                result = conn.execute(text(cleaned), params)
            else:
                result = conn.exec_driver_sql(cleaned)
            frame = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
    except Exception as exc:
        _write_log(source, sql.strip(), "error", None, str(exc), (time.perf_counter() - started) * 1000)
        raise
    _write_log(source, cleaned, "ok", len(frame), "", (time.perf_counter() - started) * 1000)
    return frame


def recent_log(limit: int = 25) -> pd.DataFrame:
    if not db_ready():
        return pd.DataFrame()
    with engine().connect() as conn:
        return pd.read_sql(
            text(
                """
                SELECT created_at, source, status, row_count, duration_ms, sql_text, error
                FROM query_log
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            conn,
            params={"limit": limit},
        )
