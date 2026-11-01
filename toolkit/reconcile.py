"""Source-to-target reconciliation checks.

Works with any Python DB-API 2.0 connection. The demo uses SQLite from the
standard library, so there are no dependencies to install.

Checks performed
  1. row_count            source vs target row counts
  2. duplicate_keys       duplicate business keys in source and in target
  3. missing_in_target    keys present in source but not in target
  4. extra_in_target      keys present in target but not in source
  5. null_count:<col>     null counts per compared column
  6. sum:<col>            totals of numeric columns (business-level aggregates)
  7. row_hash_mismatch    rows whose key matches but whose values differ

Notes for adapting to other databases
  * Table and column names are validated, then interpolated into SQL.
    Never pass untrusted user input as a name.
  * check 7 hashes rows in Python so it is portable. For large tables,
    push the hash into SQL using your database's hash function.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable, Sequence

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")

PASS, FAIL = "PASS", "FAIL"


@dataclass
class CheckResult:
    check: str
    status: str
    source_value: str
    target_value: str
    detail: str = ""


def _ident(name: str) -> str:
    if not _IDENT.match(name):
        raise ValueError(f"Unsafe or invalid identifier: {name!r}")
    return name


def _scalar(conn, sql: str):
    cur = conn.cursor()
    cur.execute(sql)
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def _rows(conn, sql: str):
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return rows


def _result(check, source_value, target_value, detail=""):
    status = PASS if source_value == target_value else FAIL
    return CheckResult(check, status, str(source_value), str(target_value), detail)


def _row_hash(values: Iterable) -> str:
    text = "\x1f".join("" if v is None else str(v) for v in values)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reconcile(
    conn,
    source: str,
    target: str,
    key_cols: Sequence[str],
    compare_cols: Sequence[str],
    numeric_cols: Sequence[str] = (),
    max_detail_rows: int = 5,
) -> list[CheckResult]:
    """Run all checks and return a list of CheckResult."""
    s, t = _ident(source), _ident(target)
    keys = [_ident(c) for c in key_cols]
    cols = [_ident(c) for c in compare_cols]
    nums = [_ident(c) for c in numeric_cols]
    results: list[CheckResult] = []

    # 1. row counts
    results.append(_result(
        "row_count",
        _scalar(conn, f"SELECT COUNT(*) FROM {s}"),
        _scalar(conn, f"SELECT COUNT(*) FROM {t}"),
    ))

    # 2. duplicate keys
    key_list = ", ".join(keys)
    for label, tbl in (("source", s), ("target", t)):
        dups = _rows(conn, f"SELECT {key_list}, COUNT(*) FROM {tbl} "
                           f"GROUP BY {key_list} HAVING COUNT(*) > 1")
        results.append(CheckResult(
            f"duplicate_keys:{label}", PASS if not dups else FAIL,
            "0", str(len(dups)),
            f"examples: {[tuple(r[:-1]) for r in dups[:max_detail_rows]]}" if dups else "",
        ))

    # 3 and 4. keys missing or extra
    join_on = " AND ".join(f"a.{k} = b.{k}" for k in keys)
    first = keys[0]
    missing = _rows(conn, f"SELECT {', '.join('a.' + k for k in keys)} FROM {s} a "
                          f"LEFT JOIN {t} b ON {join_on} WHERE b.{first} IS NULL")
    extra = _rows(conn, f"SELECT {', '.join('b.' + k for k in keys)} FROM {t} b "
                        f"LEFT JOIN {s} a ON {join_on} WHERE a.{first} IS NULL")
    results.append(CheckResult(
        "missing_in_target", PASS if not missing else FAIL, "0", str(len(missing)),
        f"examples: {[tuple(r) for r in missing[:max_detail_rows]]}" if missing else ""))
    results.append(CheckResult(
        "extra_in_target", PASS if not extra else FAIL, "0", str(len(extra)),
        f"examples: {[tuple(r) for r in extra[:max_detail_rows]]}" if extra else ""))

    # 5. null counts
    for c in cols:
        results.append(_result(
            f"null_count:{c}",
            _scalar(conn, f"SELECT COUNT(*) FROM {s} WHERE {c} IS NULL"),
            _scalar(conn, f"SELECT COUNT(*) FROM {t} WHERE {c} IS NULL"),
        ))

    # 6. numeric aggregates
    for c in nums:
        sv = _scalar(conn, f"SELECT COALESCE(SUM({c}), 0) FROM {s}")
        tv = _scalar(conn, f"SELECT COALESCE(SUM({c}), 0) FROM {t}")
        results.append(_result(f"sum:{c}", round(float(sv), 2), round(float(tv), 2)))

    # 7. row-level hash on matching keys
    sel = ", ".join(keys + cols)
    src = {tuple(r[: len(keys)]): _row_hash(r[len(keys):]) for r in _rows(conn, f"SELECT {sel} FROM {s}")}
    mismatched = []
    for r in _rows(conn, f"SELECT {sel} FROM {t}"):
        k = tuple(r[: len(keys)])
        if k in src and src[k] != _row_hash(r[len(keys):]):
            mismatched.append(k)
    results.append(CheckResult(
        "row_hash_mismatch", PASS if not mismatched else FAIL, "0", str(len(mismatched)),
        f"examples: {mismatched[:max_detail_rows]}" if mismatched else ""))
    return results


def write_results(conn, results: Sequence[CheckResult], source: str, target: str,
                  table: str = "recon_results", run_id: str | None = None) -> str:
    """Append results to an audit table (created if missing). Returns run_id."""
    _ident(table)
    run_id = run_id or uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cur = conn.cursor()
    cur.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
        run_id TEXT, run_ts TEXT, source_table TEXT, target_table TEXT,
        check_name TEXT, status TEXT, source_value TEXT, target_value TEXT, detail TEXT)""")
    for r in results:
        cur.execute(
            f"INSERT INTO {table} VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, now, source, target, r.check, r.status, r.source_value, r.target_value, r.detail),
        )
    conn.commit()
    cur.close()
    return run_id


def summarize(results: Sequence[CheckResult]) -> str:
    failed = [r for r in results if r.status == FAIL]
    lines = [f"{len(results)} checks, {len(failed)} failed"]
    for r in results:
        lines.append(f"  [{r.status}] {r.check}: source={r.source_value} target={r.target_value} {r.detail}".rstrip())
    return "\n".join(lines)


def as_dicts(results: Sequence[CheckResult]) -> list[dict]:
    return [asdict(r) for r in results]
