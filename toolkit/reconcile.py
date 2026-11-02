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
  8. null_keys:<side>     rows with a NULL in any key column (cannot be matched)

Edge cases handled (v0.2.0)
  * NULL keys are reported separately and excluded from missing/extra checks,
    because NULL never equals NULL in a SQL join.
  * Duplicate keys are reported, and are skipped in the row-level comparison
    so one duplicate does not hide or inflate value differences.
  * Numeric totals are compared with a tolerance (default 0.005), not exactly.
  * Row hashes normalize numbers (1, 1.0 and 1.000000 hash the same) and,
    optionally, text case and surrounding whitespace.
  * Empty tables are valid input.

Notes for adapting to other databases
  * Table and column names are validated, then interpolated into SQL.
    Never pass untrusted user input as a name.
  * check 7 hashes rows in Python so it is portable. For large tables,
    push the hash into SQL using your database's hash function.
"""
from __future__ import annotations

import hashlib
import numbers
import re
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable, Sequence

from .dialect import execute, table_exists

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


def _norm(v, normalize_text: bool = False) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, numbers.Number):          # int, float, Decimal
        return format(round(float(v), 6), ".6f")
    text = str(v)
    return text.strip().lower() if normalize_text else text


def _row_hash(values: Iterable, normalize_text: bool = False) -> str:
    text = "\x1f".join(_norm(v, normalize_text) for v in values)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reconcile(
    conn,
    source: str,
    target: str,
    key_cols: Sequence[str],
    compare_cols: Sequence[str],
    numeric_cols: Sequence[str] = (),
    max_detail_rows: int = 5,
    tolerance: float = 0.005,
    normalize_text: bool = False,
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

    # 2b. NULL keys cannot be matched, so report them on their own
    any_null = lambda alias: " OR ".join(f"{alias}{k} IS NULL" for k in keys)
    all_set = lambda alias: " AND ".join(f"{alias}{k} IS NOT NULL" for k in keys)
    for label, tbl in (("source", s), ("target", t)):
        n = _scalar(conn, f"SELECT COUNT(*) FROM {tbl} WHERE {any_null('')}")
        results.append(CheckResult(f"null_keys:{label}", PASS if n == 0 else FAIL, "0", str(n)))

    # 3 and 4. keys missing or extra (rows with NULL keys are excluded)
    join_on = " AND ".join(f"a.{k} = b.{k}" for k in keys)
    first = keys[0]
    missing = _rows(conn, f"SELECT {', '.join('a.' + k for k in keys)} FROM {s} a "
                          f"LEFT JOIN {t} b ON {join_on} WHERE b.{first} IS NULL AND {all_set('a.')}")
    extra = _rows(conn, f"SELECT {', '.join('b.' + k for k in keys)} FROM {t} b "
                        f"LEFT JOIN {s} a ON {join_on} WHERE a.{first} IS NULL AND {all_set('b.')}")
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
        sv, tv = float(sv), float(tv)
        ok = abs(sv - tv) <= tolerance
        results.append(CheckResult(f"sum:{c}", PASS if ok else FAIL, f"{sv:.2f}", f"{tv:.2f}",
                                   "" if ok else f"difference={tv - sv:.2f}"))

    # 7. row-level hash on matching keys (keys duplicated on either side are skipped)
    sel = ", ".join(keys + cols)
    nk = len(keys)
    src_rows, dup_src = {}, set()
    for r in _rows(conn, f"SELECT {sel} FROM {s}"):
        k = tuple(r[:nk])
        if None in k:
            continue
        if k in src_rows:
            dup_src.add(k)
        src_rows[k] = _row_hash(r[nk:], normalize_text)
    tgt_seen, dup_tgt, mismatched = {}, set(), []
    for r in _rows(conn, f"SELECT {sel} FROM {t}"):
        k = tuple(r[:nk])
        if None in k:
            continue
        if k in tgt_seen:
            dup_tgt.add(k)
        tgt_seen[k] = _row_hash(r[nk:], normalize_text)
    for k, h in tgt_seen.items():
        if k in src_rows and k not in dup_src and k not in dup_tgt and src_rows[k] != h:
            mismatched.append(k)
    skipped = len(dup_src | dup_tgt)
    note = f"; {skipped} duplicate key(s) skipped" if skipped else ""
    results.append(CheckResult(
        "row_hash_mismatch", PASS if not mismatched else FAIL, "0", str(len(mismatched)),
        (f"examples: {mismatched[:max_detail_rows]}" if mismatched else "") + note))
    return results


def write_results(conn, results: Sequence[CheckResult], source: str, target: str,
                  table: str = "recon_results", run_id: str | None = None) -> str:
    """Append results to an audit table (created if missing). Returns run_id."""
    _ident(table)
    run_id = run_id or uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not table_exists(conn, table):
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE {table} (
            run_id VARCHAR(64), run_ts VARCHAR(40), source_table VARCHAR(255), target_table VARCHAR(255),
            check_name VARCHAR(255), status VARCHAR(16), source_value VARCHAR(255),
            target_value VARCHAR(255), detail VARCHAR(4000))""")
        conn.commit()
        cur.close()
    cur = conn.cursor()
    for r in results:
        execute(cur, conn, f"INSERT INTO {table} (run_id, run_ts, source_table, target_table, check_name, "
                           "status, source_value, target_value, detail) VALUES (?,?,?,?,?,?,?,?,?)",
                (run_id, now, source, target, r.check, r.status, r.source_value, r.target_value,
                 (r.detail or "")[:4000]))
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
