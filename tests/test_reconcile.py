import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sample_data.make_sample_db import build  # noqa: E402
from toolkit import LineageLog, reconcile, write_results  # noqa: E402

COLS = ["facility_code", "encounter_date", "charge_amount", "status", "updated_at"]


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.path = "test_tmp.db"
        build(self.path)
        self.conn = sqlite3.connect(self.path)

    def tearDown(self):
        self.conn.close()
        os.remove(self.path)

    def _by_check(self):
        res = reconcile(self.conn, "src_encounters", "tgt_encounters", ["encounter_id"], COLS, ["charge_amount"])
        return {r.check: r for r in res}

    def test_detects_injected_problems(self):
        r = self._by_check()
        self.assertEqual(r["missing_in_target"].target_value, "3")
        self.assertEqual(r["extra_in_target"].target_value, "1")
        self.assertEqual(r["duplicate_keys:target"].target_value, "1")
        self.assertEqual(r["duplicate_keys:source"].status, "PASS")
        self.assertEqual(r["null_count:status"].target_value, "2")
        self.assertEqual(r["row_hash_mismatch"].status, "FAIL")
        self.assertEqual(r["sum:charge_amount"].status, "FAIL")

    def test_identical_tables_pass(self):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM tgt_encounters")
        cur.execute("INSERT INTO tgt_encounters SELECT * FROM src_encounters")
        self.conn.commit()
        res = reconcile(self.conn, "src_encounters", "tgt_encounters", ["encounter_id"], COLS, ["charge_amount"])
        self.assertTrue(all(r.status == "PASS" for r in res), [r for r in res if r.status != "PASS"])

    def test_rejects_unsafe_identifier(self):
        with self.assertRaises(ValueError):
            reconcile(self.conn, "src_encounters; DROP TABLE x", "tgt_encounters", ["encounter_id"], COLS)

    def test_audit_and_lineage_tables(self):
        res = reconcile(self.conn, "src_encounters", "tgt_encounters", ["encounter_id"], COLS)
        run_id = write_results(self.conn, res, "src_encounters", "tgt_encounters")
        n = self.conn.execute("SELECT COUNT(*) FROM recon_results WHERE run_id=?", (run_id,)).fetchone()[0]
        self.assertEqual(n, len(res))
        LineageLog(self.conn).record("step", "a", "b", "copy", 1, 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM lineage_log").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
