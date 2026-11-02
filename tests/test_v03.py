import json
import os
import sqlite3
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sample_data.make_healthcare_sample_db import build_into as build_hc  # noqa: E402
from toolkit import LineageLog, check_incremental, reconcile, rules, write_results  # noqa: E402
from toolkit import dialect  # noqa: E402
from toolkit.reconcile import _norm  # noqa: E402


def mem():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE p (a INTEGER, b TEXT, c TEXT)")
    return c


class UniqueNullPolicy(unittest.TestCase):
    def setUp(self):
        self.c = mem()
        # (1,x) x2 -> true duplicate; (1,NULL) x2 -> duplicate only if NULLs are equal; (NULL,NULL) x2
        for row in [(1, "x", "k"), (1, "x", "k"), (1, None, "k"), (1, None, "k"), (None, None, "k"), (None, None, "k")]:
            self.c.execute("INSERT INTO p VALUES (?,?,?)", row)

    def test_ignore_skips_rows_with_any_null(self):
        r = rules.unique(self.c, "p", ["a", "b"])
        self.assertEqual(r.target_value, "1")            # only (1,'x')

    def test_strict_treats_nulls_as_equal(self):
        r = rules.unique(self.c, "p", ["a", "b"], null_policy="strict")
        self.assertEqual(r.target_value, "3")            # (1,x), (1,NULL), (NULL,NULL)

    def test_null_in_second_column_only(self):
        r = rules.unique(self.c, "p", ["c", "b"])        # first column never NULL
        self.assertEqual(r.target_value, "1")            # (k,'x'); (k,NULL) rows ignored

    def test_bad_policy_rejected(self):
        with self.assertRaises(ValueError):
            rules.unique(self.c, "p", ["a"], null_policy="maybe")


class IncrementalEmptyTarget(unittest.TestCase):
    def test_same_checks_whether_or_not_target_is_empty(self):
        c = sqlite3.connect(":memory:")
        for t in ("s", "t"):
            c.execute(f"CREATE TABLE {t} (id INTEGER, ts TEXT)")
        c.execute("INSERT INTO s VALUES (1,'2026-01-01')")
        c.execute("INSERT INTO s VALUES (2,'2026-01-02')")
        c.execute("INSERT INTO s VALUES (3,NULL)")
        empty = {r.check: r for r in check_incremental(c, "s", "t", ["id"], "ts")}
        c.execute("INSERT INTO t VALUES (1,'2026-01-01')")
        loaded = {r.check: r for r in check_incremental(c, "s", "t", ["id"], "ts")}
        self.assertEqual(set(empty), set(loaded))
        self.assertEqual(empty["null_timestamps"].target_value, "1")
        self.assertEqual(empty["pending_after_watermark"].target_value, "2")   # null ts excluded
        self.assertEqual(loaded["pending_after_watermark"].target_value, "1")
        self.assertEqual(loaded["null_timestamps"].target_value, "1")

    def test_both_empty(self):
        c = sqlite3.connect(":memory:")
        for t in ("s", "t"):
            c.execute(f"CREATE TABLE {t} (id INTEGER, ts TEXT)")
        r = {x.check: x for x in check_incremental(c, "s", "t", ["id"], "ts")}
        self.assertEqual(r["pending_after_watermark"].target_value, "0")
        self.assertEqual(r["late_arriving_missing"].status, "PASS")


class Lineage(unittest.TestCase):
    def test_run_id_status_version(self):
        c = sqlite3.connect(":memory:")
        log = LineageLog(c, run_id="run-1")
        with log.step("load", "a", "b", "copy") as s:
            s.rows_in, s.rows_out, s.note = 10, 9, "one rejected"
        rows = json.loads(log.to_json())
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["run_id"], r["status"], r["rows_in"], r["rows_out"]), ("run-1", "SUCCESS", 10, 9))
        self.assertTrue(r["toolkit_version"])
        self.assertIsNotNone(r["duration_ms"])

    def test_failure_is_logged_and_reraised(self):
        c = sqlite3.connect(":memory:")
        log = LineageLog(c, run_id="run-2")
        with self.assertRaises(RuntimeError):
            with log.step("bad", "a", "b", "boom"):
                raise RuntimeError("disk full")
        r = json.loads(log.to_json())[0]
        self.assertEqual(r["status"], "FAILED")
        self.assertIn("RuntimeError: disk full", r["error_detail"])

    def test_runs_are_separated_and_invalid_status_rejected(self):
        c = sqlite3.connect(":memory:")
        a, b = LineageLog(c, run_id="A"), LineageLog(c, run_id="B")
        a.record("s1", "x", "y", "t"); b.record("s2", "x", "y", "t"); b.record("s3", "x", "y", "t")
        self.assertEqual(len(json.loads(a.to_json())), 1)
        self.assertEqual(len(json.loads(b.to_json())), 2)
        self.assertEqual(len(json.loads(a.to_json(all_runs=True))), 3)
        with self.assertRaises(ValueError):
            a.record("s", "x", "y", "t", status="DONE")


class Dialect(unittest.TestCase):
    def _conn(self, style):
        mod = type(sys)("fakedriver")
        mod.paramstyle = style
        sys.modules["fakedriver"] = mod
        cls = type("FakeConn", (), {"__module__": "fakedriver.connection"})
        return cls()

    def tearDown(self):
        sys.modules.pop("fakedriver", None)

    def test_placeholder_styles(self):
        self.assertEqual(dialect.placeholders(self._conn("qmark"), 2), ["?", "?"])
        self.assertEqual(dialect.placeholders(self._conn("pyformat"), 2), ["%s", "%s"])
        self.assertEqual(dialect.placeholders(self._conn("format"), 1), ["%s"])
        self.assertEqual(dialect.placeholders(self._conn("numeric"), 2), [":1", ":2"])
        self.assertEqual(dialect.params(self._conn("named"), [5, 6]), {"p1": 5, "p2": 6})

    def test_unsupported_style_raises(self):
        with self.assertRaises(ValueError):
            dialect.placeholders(self._conn("weird"), 1)

    def test_sqlite_is_qmark(self):
        self.assertEqual(dialect.placeholders(sqlite3.connect(":memory:"), 1), ["?"])


class Normalization(unittest.TestCase):
    def test_decimal_float_int_hash_equal(self):
        self.assertEqual(_norm(Decimal("10.50")), _norm(10.5))
        self.assertEqual(_norm(10), _norm(10.0))
        self.assertEqual(_norm(None), "")


class Integration(unittest.TestCase):
    def test_pipeline_run_is_traceable_end_to_end(self):
        c = sqlite3.connect(":memory:")
        build_hc(c)
        results = [rules.referential_integrity(c, "claims", "encounter_id", "encounters", "encounter_id"),
                   rules.unique(c, "patients", ["patient_id"])]
        run_id = write_results(c, results, "healthcare_sample", "integrity_rules")
        log = LineageLog(c, run_id=run_id)
        with log.step("validate_claims", "claims", "recon_results", "rule checks") as s:
            s.rows_in = c.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
            s.rows_out = len(results)
        stored = c.execute("SELECT check_name, status FROM recon_results WHERE run_id=?", (run_id,)).fetchall()
        self.assertEqual(len(stored), 2)
        self.assertEqual({r[1] for r in stored}, {"FAIL", "PASS"})
        lineage = json.loads(log.to_json())
        self.assertEqual(lineage[0]["run_id"], run_id)
        self.assertEqual(lineage[0]["rows_in"], 252)

    def test_write_results_twice_appends_not_recreates(self):
        c = sqlite3.connect(":memory:")
        r = reconcile(c.execute("CREATE TABLE s (id INTEGER)") and c, "s", "s", ["id"], [])
        write_results(c, r, "s", "s", run_id="r1")
        write_results(c, r, "s", "s", run_id="r2")
        n = c.execute("SELECT COUNT(DISTINCT run_id) FROM recon_results").fetchone()[0]
        self.assertEqual(n, 2)


class RuleEdgeCases(unittest.TestCase):
    def test_allowed_values_empty_list_rejected(self):
        with self.assertRaises(ValueError):
            rules.allowed_values(mem(), "p", "b", [])

    def test_date_order_ignores_nulls_and_equal_dates(self):
        c = sqlite3.connect(":memory:")
        c.execute("CREATE TABLE d (s TEXT, e TEXT)")
        c.executemany("INSERT INTO d VALUES (?,?)", [("2026-01-01", "2026-01-01"), (None, "2026-01-01"), ("2026-01-02", None)])
        self.assertEqual(rules.date_order(c, "d", "s", "e").status, "PASS")

    def test_amount_tolerance(self):
        c = sqlite3.connect(":memory:")
        c.execute("CREATE TABLE par (id INTEGER, amt REAL)")
        c.execute("CREATE TABLE ch (id INTEGER, amt REAL)")
        c.execute("INSERT INTO par VALUES (1, 100.0)")
        c.execute("INSERT INTO ch VALUES (1, 100.004)")
        self.assertEqual(rules.amount_matches_parent(c, "ch", "id", "amt", "par", "id", "amt").status, "PASS")
        self.assertEqual(rules.amount_matches_parent(c, "ch", "id", "amt", "par", "id", "amt", tolerance=0.001).status, "FAIL")


if __name__ == "__main__":
    unittest.main()
