"""Incremental-load (watermark) validation.

An incremental load copies only rows newer than the target's high-water mark.
That is fast, but it can silently lose data. These checks look for the usual
ways that happens.

Checks
  null_timestamps       source rows with no timestamp (a watermark cannot see them)
  late_arriving_missing source rows at or before the target watermark whose key is
                        not in the target (they were skipped by the watermark)
  target_ahead          target rows newer than anything in the source
  pending_after_watermark  source rows newer than the target watermark (INFO only:
                        expected before the next load runs)
  watermark             INFO row showing the target's high-water mark

The same set of checks is always returned. If the target is empty there is no
watermark yet, so every source row with a timestamp counts as pending.

Timestamps are compared as given. Use one consistent format (for example ISO 8601
text) so that string order matches time order. Parameters use the driver's own
placeholder style (see dialect.py).
"""
from __future__ import annotations

from typing import Sequence

from .dialect import execute
from .reconcile import FAIL, PASS, CheckResult, _ident, _rows, _scalar

INFO = "INFO"


def check_incremental(conn, source: str, target: str, key_cols: Sequence[str],
                      ts_col: str, max_detail_rows: int = 5) -> list[CheckResult]:
    s, t, ts = _ident(source), _ident(target), _ident(ts_col)
    keys = [_ident(c) for c in key_cols]
    join_on = " AND ".join(f"a.{k} = b.{k}" for k in keys)
    first = keys[0]
    key_sel = ", ".join("a." + k for k in keys)
    results: list[CheckResult] = []

    n_null = _scalar(conn, f"SELECT COUNT(*) FROM {s} WHERE {ts} IS NULL")
    results.append(CheckResult("null_timestamps", PASS if n_null == 0 else FAIL, "0", str(n_null)))

    wm = _scalar(conn, f"SELECT MAX({ts}) FROM {t}")
    src_max = _scalar(conn, f"SELECT MAX({ts}) FROM {s}")
    cur = conn.cursor()
    if wm is None:
        # No watermark yet: nothing can be late, and every timestamped source row is pending.
        pending = _scalar(conn, f"SELECT COUNT(*) FROM {s} WHERE {ts} IS NOT NULL")
        results.append(CheckResult("watermark", INFO, str(src_max), "None",
                                   "target is empty; no watermark yet"))
        results.append(CheckResult("late_arriving_missing", PASS, "0", "0", "no watermark yet"))
        results.append(CheckResult("target_ahead", PASS, "0", "0"))
        results.append(CheckResult("pending_after_watermark", INFO, "0", str(pending),
                                   "all timestamped source rows are pending"))
        cur.close()
        return results

    execute(cur, conn, f"SELECT {key_sel} FROM {s} a LEFT JOIN {t} b ON {join_on} "
                       f"WHERE b.{first} IS NULL AND a.{ts} <= ?", (wm,))
    late = cur.fetchall()
    execute(cur, conn, f"SELECT COUNT(*) FROM {s} WHERE {ts} > ?", (wm,))
    pending = cur.fetchone()[0]
    ahead = 0
    if src_max is not None:
        execute(cur, conn, f"SELECT COUNT(*) FROM {t} WHERE {ts} > ?", (src_max,))
        ahead = cur.fetchone()[0]
    cur.close()

    results.append(CheckResult("watermark", INFO, str(src_max), str(wm)))
    results.append(CheckResult(
        "late_arriving_missing", PASS if not late else FAIL, "0", str(len(late)),
        f"watermark={wm}; examples: {[tuple(r) for r in late[:max_detail_rows]]}" if late else ""))
    results.append(CheckResult("target_ahead", PASS if ahead == 0 else FAIL, "0", str(ahead)))
    results.append(CheckResult("pending_after_watermark", INFO, "0", str(pending),
                               "expected until the next incremental run"))
    return results
