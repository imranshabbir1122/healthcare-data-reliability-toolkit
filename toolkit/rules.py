"""Single-dataset integrity rules (no source/target pair needed).

Each function returns a CheckResult. Convention matches reconcile.py:
source_value is the expected number of violations ("0"), target_value is the
number found. PASS means zero violations.

Rules
  not_null              NULL values in a column
  unique                duplicate values (or combinations) in column(s)
  allowed_values        values outside an agreed list
  referential_integrity child rows whose parent key does not exist
  date_order            rows where an end date is before a start date
  amount_matches_parent child amounts that disagree with the parent amount
  orphan_children       alias of referential_integrity, reads better for claims/events

Dates are expected as ISO 8601 text (YYYY-MM-DD) so string order equals date order.
Parameters use the driver's own placeholder style (see dialect.py).

NULL behavior of unique()
  null_policy="ignore" (default): a row with a NULL in ANY listed column is not
  counted as a duplicate. This matches the SQL standard and the UNIQUE constraint
  in PostgreSQL and SQLite. null_policy="strict": NULLs are treated as equal
  values, so two rows with the same non-NULL parts and NULL elsewhere are
  duplicates. SQL Server's UNIQUE constraint behaves this way, so use "strict"
  there. Single-column and composite keys follow the same rule.
"""
from __future__ import annotations

from typing import Sequence

from .dialect import execute
from .reconcile import FAIL, PASS, CheckResult, _ident, _rows, _scalar


def _res(name: str, rows, max_detail_rows: int = 5, extra: str = "") -> CheckResult:
    n = len(rows)
    detail = f"examples: {[tuple(r) for r in rows[:max_detail_rows]]}" if n else ""
    return CheckResult(name, PASS if n == 0 else FAIL, "0", str(n), (detail + " " + extra).strip())


def not_null(conn, table: str, col: str) -> CheckResult:
    t, c = _ident(table), _ident(col)
    n = _scalar(conn, f"SELECT COUNT(*) FROM {t} WHERE {c} IS NULL")
    return CheckResult(f"not_null:{table}.{col}", PASS if n == 0 else FAIL, "0", str(n))


def unique(conn, table: str, cols: Sequence[str], null_policy: str = "ignore") -> CheckResult:
    if null_policy not in ("ignore", "strict"):
        raise ValueError("null_policy must be 'ignore' or 'strict'")
    t = _ident(table)
    names = [_ident(c) for c in cols]
    cs = ", ".join(names)
    where = ""
    if null_policy == "ignore":
        where = "WHERE " + " AND ".join(f"{c} IS NOT NULL" for c in names) + " "
    rows = _rows(conn, f"SELECT {cs}, COUNT(*) FROM {t} {where}GROUP BY {cs} HAVING COUNT(*) > 1")
    return _res(f"unique:{table}({','.join(cols)}):{null_policy}", [r[:-1] for r in rows])


def allowed_values(conn, table: str, col: str, allowed: Sequence[str]) -> CheckResult:
    t, c = _ident(table), _ident(col)
    if not allowed:
        raise ValueError("allowed must contain at least one value")
    marks = ", ".join("?" for _ in allowed)
    cur = conn.cursor()
    execute(cur, conn, f"SELECT {c}, COUNT(*) FROM {t} WHERE {c} IS NOT NULL AND {c} NOT IN ({marks}) GROUP BY {c}",
            tuple(allowed))
    rows = cur.fetchall()
    cur.close()
    n = sum(r[1] for r in rows)
    return CheckResult(f"allowed_values:{table}.{col}", PASS if n == 0 else FAIL, "0", str(n),
                       f"unexpected values: {[r[0] for r in rows[:5]]}" if rows else "")


def referential_integrity(conn, child: str, child_col: str, parent: str, parent_col: str) -> CheckResult:
    ch, cc, pa, pc = _ident(child), _ident(child_col), _ident(parent), _ident(parent_col)
    rows = _rows(conn, f"SELECT c.{cc} FROM {ch} c LEFT JOIN {pa} p ON c.{cc} = p.{pc} "
                       f"WHERE c.{cc} IS NOT NULL AND p.{pc} IS NULL")
    return _res(f"referential_integrity:{child}.{child_col}->{parent}.{parent_col}", rows)


orphan_children = referential_integrity


def date_order(conn, table: str, earlier_col: str, later_col: str) -> CheckResult:
    t, e, l = _ident(table), _ident(earlier_col), _ident(later_col)
    rows = _rows(conn, f"SELECT {e}, {l} FROM {t} WHERE {e} IS NOT NULL AND {l} IS NOT NULL AND {l} < {e}")
    return _res(f"date_order:{table}.{later_col}>={earlier_col}", rows)


def amount_matches_parent(conn, child: str, child_fk: str, child_amt: str,
                          parent: str, parent_pk: str, parent_amt: str,
                          tolerance: float = 0.005) -> CheckResult:
    ch, fk, ca = _ident(child), _ident(child_fk), _ident(child_amt)
    pa, pk, pm = _ident(parent), _ident(parent_pk), _ident(parent_amt)
    rows = _rows(conn, f"SELECT c.{fk}, c.{ca}, p.{pm} FROM {ch} c JOIN {pa} p ON c.{fk} = p.{pk} "
                       f"WHERE ABS(COALESCE(c.{ca}, 0) - COALESCE(p.{pm}, 0)) > {float(tolerance)}")
    return _res(f"amount_matches:{child}.{child_amt}~{parent}.{parent_amt}", rows)
