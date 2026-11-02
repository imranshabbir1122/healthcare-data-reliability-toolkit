"""Lineage and run log.

One row per processing step: what came from where, which transformation ran,
how many rows went in and out, whether it succeeded, and which toolkit version
recorded it. Rows share a run_id so one pipeline run can be reviewed together.

    log = LineageLog(conn, run_id=run_id)
    with log.step("load_encounters", "raw.enc", "curated.enc", "dedupe + cast") as s:
        ...                      # do the work
        s.rows_in, s.rows_out = 200, 199
    # an exception inside the block is recorded as FAILED with the error text,
    # then re-raised, so a failure never disappears from the log.

Statuses: SUCCESS, FAILED, WARNING, SKIPPED.

Schema change in 0.3.0: columns run_id, seq, status, error_detail, duration_ms and
toolkit_version were added. A lineage_log table created by 0.1.x or 0.2.x must be
dropped or migrated by hand. The table is created with portable DDL.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from ._version import __version__
from .dialect import execute, table_exists

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")
STATUSES = ("SUCCESS", "FAILED", "WARNING", "SKIPPED")
_COLS = ("step_id", "run_id", "seq", "step_ts", "step_name", "source", "target", "transformation",
         "rows_in", "rows_out", "status", "error_detail", "duration_ms", "toolkit_version", "note")


class _Step:
    def __init__(self):
        self.rows_in = None
        self.rows_out = None
        self.note = ""
        self.status = "SUCCESS"


class LineageLog:
    def __init__(self, conn, table: str = "lineage_log", run_id: str | None = None):
        if not _IDENT.match(table):
            raise ValueError("invalid table name")
        self.conn, self.table = conn, table
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self._seq = 0
        if not table_exists(conn, table):
            cur = conn.cursor()
            cur.execute(f"""CREATE TABLE {table} (
                step_id VARCHAR(40), run_id VARCHAR(64), seq INTEGER, step_ts VARCHAR(40),
                step_name VARCHAR(255), source VARCHAR(255), target VARCHAR(255),
                transformation VARCHAR(1000), rows_in INTEGER, rows_out INTEGER,
                status VARCHAR(16), error_detail VARCHAR(2000), duration_ms INTEGER,
                toolkit_version VARCHAR(16), note VARCHAR(2000))""")
            conn.commit()
            cur.close()

    def record(self, step_name: str, source: str, target: str, transformation: str,
               rows_in: int | None = None, rows_out: int | None = None, note: str = "",
               status: str = "SUCCESS", error_detail: str = "", duration_ms: int | None = None) -> str:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        self._seq += 1
        step_id = uuid.uuid4().hex[:16]
        cur = self.conn.cursor()
        execute(cur, self.conn,
                f"INSERT INTO {self.table} ({', '.join(_COLS)}) VALUES ({', '.join('?' for _ in _COLS)})",
                (step_id, self.run_id, self._seq,
                 datetime.now(timezone.utc).isoformat(timespec="milliseconds"), step_name, source,
                 target, transformation, rows_in, rows_out, status, (error_detail or "")[:2000],
                 duration_ms, __version__, (note or "")[:2000]))
        self.conn.commit()
        cur.close()
        return step_id

    @contextmanager
    def step(self, step_name: str, source: str, target: str, transformation: str):
        s = _Step()
        start = time.monotonic()
        try:
            yield s
        except Exception as exc:
            args = (step_name, source, target, transformation, s.rows_in, s.rows_out, s.note,
                    "FAILED", f"{type(exc).__name__}: {exc}", int((time.monotonic() - start) * 1000))
            try:
                self.record(*args)
            except Exception:
                # e.g. PostgreSQL leaves the transaction aborted after an error: roll back, retry once
                if hasattr(self.conn, "rollback"):
                    self.conn.rollback()
                self.record(*args)
            raise
        else:
            self.record(step_name, source, target, transformation, s.rows_in, s.rows_out, s.note,
                        s.status, "", int((time.monotonic() - start) * 1000))

    def to_json(self, all_runs: bool = False) -> str:
        cur = self.conn.cursor()
        sql = f"SELECT {', '.join(_COLS)} FROM {self.table}"
        if all_runs:
            cur.execute(sql + " ORDER BY step_ts, seq")
        else:
            execute(cur, self.conn, sql + " WHERE run_id = ? ORDER BY seq", (self.run_id,))
        out = [dict(zip(_COLS, r)) for r in cur.fetchall()]
        cur.close()
        return json.dumps(out, indent=2)
