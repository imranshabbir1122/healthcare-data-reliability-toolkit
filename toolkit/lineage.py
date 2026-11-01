"""Minimal lineage and provenance log.

Records one row per processing step: what came from where, which rule or
transformation was applied, and how many rows went in and out. Stored in a
table so it can be queried, and exportable to JSON for review.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class LineageLog:
    def __init__(self, conn, table: str = "lineage_log"):
        if not _IDENT.match(table):
            raise ValueError("invalid table name")
        self.conn, self.table = conn, table
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
            step_id INTEGER PRIMARY KEY AUTOINCREMENT,
            step_ts TEXT, step_name TEXT, source TEXT, target TEXT,
            transformation TEXT, rows_in INTEGER, rows_out INTEGER, note TEXT)""")
        conn.commit()
        cur.close()

    def record(self, step_name: str, source: str, target: str, transformation: str,
               rows_in: int | None = None, rows_out: int | None = None, note: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            f"INSERT INTO {self.table} (step_ts, step_name, source, target, transformation, rows_in, rows_out, note) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), step_name, source,
             target, transformation, rows_in, rows_out, note),
        )
        self.conn.commit()
        cur.close()

    def to_json(self) -> str:
        cur = self.conn.cursor()
        cur.execute(f"SELECT step_id, step_ts, step_name, source, target, transformation, "
                    f"rows_in, rows_out, note FROM {self.table} ORDER BY step_id")
        names = [d[0] for d in cur.description]
        out = [dict(zip(names, r)) for r in cur.fetchall()]
        cur.close()
        return json.dumps(out, indent=2)
