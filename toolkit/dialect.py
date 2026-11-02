"""Small helpers that keep the Python module portable across DB-API drivers.

Drivers use different parameter placeholder styles (sqlite3 and pyodbc use "?",
psycopg2 uses "%s", some use ":name"). `placeholders` asks the driver module
which style it uses, so the toolkit does not hard-code SQLite's "?".

Tested drivers: sqlite3 and psycopg2 (PostgreSQL 16). Other drivers should work if
they follow the DB-API 2.0 `paramstyle` convention, but have not been tested.
"""
from __future__ import annotations

import sys


def paramstyle(conn) -> str:
    mod = sys.modules.get(type(conn).__module__.split(".")[0])
    return getattr(mod, "paramstyle", "qmark")


def placeholders(conn, n: int) -> list[str]:
    style = paramstyle(conn)
    if style == "qmark":
        return ["?"] * n
    if style in ("format", "pyformat"):
        return ["%s"] * n
    if style == "numeric":
        return [f":{i}" for i in range(1, n + 1)]
    if style == "named":
        return [f":p{i}" for i in range(1, n + 1)]
    raise ValueError(f"unsupported paramstyle: {style}")


def params(conn, values):
    """Return values in the form the driver expects (dict for named style)."""
    values = tuple(values)
    if paramstyle(conn) == "named":
        return {f"p{i}": v for i, v in enumerate(values, start=1)}
    return values


def execute(cur, conn, sql_with_qmarks: str, values=()):
    """Run SQL written with "?" markers using the driver's own placeholder style."""
    values = tuple(values)
    marks = placeholders(conn, len(values))
    parts = sql_with_qmarks.split("?")
    if len(parts) - 1 != len(values):
        raise ValueError("placeholder count does not match values")
    sql = parts[0]
    for m, tail in zip(marks, parts[1:]):
        sql += m + tail
    cur.execute(sql, params(conn, values))


def table_exists(conn, table: str) -> bool:
    """Portable existence test that avoids CREATE TABLE IF NOT EXISTS (not in SQL Server)."""
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT 1 FROM {table} WHERE 1 = 0")
        cur.fetchall()
        return True
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        return False
    finally:
        cur.close()
