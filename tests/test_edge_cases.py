import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from toolkit import check_incremental, reconcile  # noqa: E402


def mk():
    c = sqlite3.connect(":memory:")
    for t in ("s", "t"):
        c.execute(f"CREATE TABLE {t} (id INTEGER, name TEXT, amt REAL, ts TEXT)")
    return c


def by(res):
    return {r.check: r for r in res}


class EdgeCases(unittest.TestCase):
    def test_empty_tables(self):
        c = mk()
        r = reconcile(c, "s", "t", ["id"], ["name"], ["amt"])
        self.assertTrue(all(x.status == "PASS" for x in r))

    def test_null_keys_reported_not_missing(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (NULL,'a',1,'2026-01-01')")
        c.execute("INSERT INTO t VALUES (NULL,'a',1,'2026-01-01')")
        r = by(reconcile(c, "s", "t", ["id"], ["name"]))
        self.assertEqual(r["null_keys:source"].target_value, "1")
        self.assertEqual(r["null_keys:target"].target_value, "1")
        self.assertEqual(r["missing_in_target"].status, "PASS")
        self.assertEqual(r["extra_in_target"].status, "PASS")

    def test_float_normalization_and_tolerance(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (1,'a',10.0,'x')")
        c.execute("INSERT INTO t VALUES (1,'a',10.004,'x')")
        r = by(reconcile(c, "s", "t", ["id"], ["amt"], ["amt"]))
        self.assertEqual(r["sum:amt"].status, "PASS")          # within 0.005
        self.assertEqual(r["row_hash_mismatch"].status, "FAIL")  # 6-decimal hash sees it
        r2 = by(reconcile(c, "s", "t", ["id"], ["amt"], ["amt"], tolerance=0.0001))
        self.assertEqual(r2["sum:amt"].status, "FAIL")

    def test_int_and_float_hash_equal(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (1,'a',5,'x')")
        c.execute("INSERT INTO t VALUES (1,'a',5.0,'x')")
        r = by(reconcile(c, "s", "t", ["id"], ["amt"]))
        self.assertEqual(r["row_hash_mismatch"].status, "PASS")

    def test_text_normalization_optional(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (1,'Smith',1,'x')")
        c.execute("INSERT INTO t VALUES (1,' smith ',1,'x')")
        self.assertEqual(by(reconcile(c, "s", "t", ["id"], ["name"]))["row_hash_mismatch"].status, "FAIL")
        self.assertEqual(by(reconcile(c, "s", "t", ["id"], ["name"], normalize_text=True))["row_hash_mismatch"].status, "PASS")

    def test_duplicate_keys_skipped_in_hash(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (1,'a',1,'x')")
        c.execute("INSERT INTO t VALUES (1,'a',1,'x')")
        c.execute("INSERT INTO t VALUES (1,'a',1,'x')")
        r = by(reconcile(c, "s", "t", ["id"], ["name"]))
        self.assertEqual(r["duplicate_keys:target"].status, "FAIL")
        self.assertEqual(r["row_hash_mismatch"].status, "PASS")
        self.assertIn("skipped", r["row_hash_mismatch"].detail)

    def test_composite_keys(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (1,'a',1,'x')")
        c.execute("INSERT INTO s VALUES (1,'b',1,'x')")
        c.execute("INSERT INTO t VALUES (1,'a',1,'x')")
        r = by(reconcile(c, "s", "t", ["id", "name"], ["amt"]))
        self.assertEqual(r["missing_in_target"].target_value, "1")


class Incremental(unittest.TestCase):
    def test_clean_load(self):
        c = mk()
        for i in (1, 2, 3):
            c.execute("INSERT INTO s VALUES (?,?,?,?)", (i, "a", 1, f"2026-01-0{i}"))
            c.execute("INSERT INTO t VALUES (?,?,?,?)", (i, "a", 1, f"2026-01-0{i}"))
        r = by(check_incremental(c, "s", "t", ["id"], "ts"))
        self.assertEqual(r["late_arriving_missing"].status, "PASS")
        self.assertEqual(r["target_ahead"].status, "PASS")

    def test_late_arriving_row_is_caught(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (1,'a',1,'2026-01-01')")
        c.execute("INSERT INTO s VALUES (2,'a',1,'2026-01-02')")   # skipped by watermark
        c.execute("INSERT INTO s VALUES (3,'a',1,'2026-01-03')")
        c.execute("INSERT INTO t VALUES (1,'a',1,'2026-01-01')")
        c.execute("INSERT INTO t VALUES (3,'a',1,'2026-01-03')")
        r = by(check_incremental(c, "s", "t", ["id"], "ts"))
        self.assertEqual(r["late_arriving_missing"].target_value, "1")

    def test_pending_rows_are_info_not_failure(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (1,'a',1,'2026-01-01')")
        c.execute("INSERT INTO s VALUES (2,'a',1,'2026-01-05')")
        c.execute("INSERT INTO t VALUES (1,'a',1,'2026-01-01')")
        r = by(check_incremental(c, "s", "t", ["id"], "ts"))
        self.assertEqual(r["pending_after_watermark"].status, "INFO")
        self.assertEqual(r["late_arriving_missing"].status, "PASS")

    def test_null_timestamp_and_target_ahead(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (1,'a',1,NULL)")
        c.execute("INSERT INTO t VALUES (9,'a',1,'2027-01-01')")
        r = by(check_incremental(c, "s", "t", ["id"], "ts"))
        self.assertEqual(r["null_timestamps"].status, "FAIL")

    def test_empty_target(self):
        c = mk()
        c.execute("INSERT INTO s VALUES (1,'a',1,'2026-01-01')")
        r = check_incremental(c, "s", "t", ["id"], "ts")
        self.assertEqual(by(r)["watermark"].status, "INFO")


if __name__ == "__main__":
    unittest.main()
