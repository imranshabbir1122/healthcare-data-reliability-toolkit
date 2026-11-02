"""PostgreSQL integration tests.

Skipped unless TOOLKIT_PG_DSN is set and psycopg2 is installed. Use a THROWAWAY
database: the tests create and drop the sample tables, recon_results and lineage_log.

    TOOLKIT_PG_DSN="host=localhost dbname=scratch user=me password=..." python -m unittest tests.test_postgres
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DSN = os.environ.get("TOOLKIT_PG_DSN")
try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None


@unittest.skipUnless(DSN and psycopg2, "set TOOLKIT_PG_DSN and install psycopg2 to run")
class PostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sample_data.make_healthcare_sample_db import build_into as hc
        from sample_data.make_sample_db import build_into as enc
        cls.conn = psycopg2.connect(DSN)
        for t in ("recon_results", "lineage_log"):
            cur = cls.conn.cursor(); cur.execute(f"DROP TABLE IF EXISTS {t}"); cls.conn.commit(); cur.close()
        hc(cls.conn)
        enc(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cur = cls.conn.cursor()
        for t in ("recon_results", "lineage_log", "claims", "clinical_events", "encounters", "patients",
                  "facilities", "src_encounters", "tgt_encounters"):
            cur.execute(f"DROP TABLE IF EXISTS {t}")
        cls.conn.commit(); cur.close(); cls.conn.close()

    def test_reconcile_matches_sqlite_results(self):
        from toolkit import reconcile
        cols = ["facility_code", "encounter_date", "charge_amount", "status", "updated_at"]
        r = {x.check: x for x in reconcile(self.conn, "src_encounters", "tgt_encounters",
                                           ["encounter_id"], cols, ["charge_amount"])}
        self.assertEqual(r["missing_in_target"].target_value, "3")
        self.assertEqual(r["extra_in_target"].target_value, "1")
        self.assertEqual(r["duplicate_keys:target"].target_value, "1")
        self.assertEqual(r["null_count:status"].target_value, "2")
        self.assertEqual(r["row_hash_mismatch"].target_value, "4")   # same as SQLite
        self.assertEqual(r["sum:charge_amount"].status, "FAIL")

    def test_rules_match_sqlite_counts(self):
        from toolkit import rules
        c = self.conn
        n = lambda res: int(res.target_value)
        self.assertEqual(n(rules.referential_integrity(c, "encounters", "patient_id", "patients", "patient_id")), 2)
        self.assertEqual(n(rules.referential_integrity(c, "claims", "encounter_id", "encounters", "encounter_id")), 2)
        self.assertEqual(n(rules.date_order(c, "encounters", "admit_date", "discharge_date")), 2)
        self.assertEqual(n(rules.unique(c, "patients", ["mrn"])), 1)
        self.assertEqual(n(rules.allowed_values(c, "encounters", "encounter_type",
                                                ["INPATIENT", "OUTPATIENT", "EMERGENCY"])), 2)
        self.assertEqual(n(rules.amount_matches_parent(c, "claims", "encounter_id", "billed_amount",
                                                       "encounters", "encounter_id", "charge_amount")), 3)

    def test_audit_and_lineage_roundtrip(self):
        from toolkit import LineageLog, reconcile, write_results
        res = reconcile(self.conn, "src_encounters", "tgt_encounters", ["encounter_id"], ["status"])
        run_id = write_results(self.conn, res, "src_encounters", "tgt_encounters")
        log = LineageLog(self.conn, run_id=run_id)
        with log.step("check", "src_encounters", "tgt_encounters", "reconcile") as s:
            s.rows_in, s.rows_out = 200, 199
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM recon_results WHERE run_id = %s", (run_id,))
        self.assertEqual(cur.fetchone()[0], len(res))
        cur.close()
        self.assertEqual(json.loads(log.to_json())[0]["status"], "SUCCESS")

    def test_failed_step_logged_after_driver_error(self):
        from toolkit import LineageLog
        log = LineageLog(self.conn, run_id="pg-fail")
        with self.assertRaises(Exception):
            with log.step("bad_sql", "x", "y", "select"):
                cur = self.conn.cursor()
                try:
                    cur.execute("SELECT * FROM table_that_does_not_exist")
                except Exception:
                    self.conn.rollback()      # PostgreSQL aborts the transaction on error
                    raise
        self.assertEqual(json.loads(log.to_json())[0]["status"], "FAILED")

    def _run_sql_file(self, rel):
        path = os.path.join(os.path.dirname(__file__), "..", rel)
        text = "\n".join(l for l in open(path).read().splitlines() if not l.strip().startswith("--"))
        out = []
        for stmt in [x.strip() for x in text.split(";") if x.strip()]:
            cur = self.conn.cursor()
            cur.execute(stmt)
            out.append(cur.fetchall() if cur.description else None)
            cur.close()
        self.conn.commit()
        return out

    def test_postgresql_sql_files(self):
        diff = self._run_sql_file("sql/postgresql/05_value_differences.sql")[0]
        self.assertEqual(len(diff), 4)                      # 2 changed amounts + 2 null statuses
        hashed = self._run_sql_file("sql/postgresql/09_row_hash.sql")[0]
        self.assertEqual(len(hashed), 4)                    # agrees with the value comparison
        wm = self._run_sql_file("sql/postgresql/06_incremental_watermark.sql")
        self.assertIsNotNone(wm[2])                         # late-arriving query executes
        self.assertEqual(len(wm[0]), 1)

    def test_shared_sql_files_run_on_postgresql(self):
        for f in ("sql/01_row_counts.sql", "sql/02_key_checks.sql", "sql/03_null_checks.sql",
                  "sql/04_aggregate_reconciliation.sql"):
            self._run_sql_file(f)
        missing = self._run_sql_file("sql/02_key_checks.sql")[1]
        self.assertEqual(len(missing), 3)
        # integrity rules: orphan encounters 2, discharge-before-admit 2, duplicate MRN 1
        rules_out = self._run_sql_file("sql/08_integrity_rules.sql")
        self.assertEqual([len(r) for r in rules_out], [2, 2, 1, 2, 3])

    def test_audit_ddl_runs_on_postgresql(self):
        cur = self.conn.cursor()
        for t in ("recon_results", "lineage_log"):
            cur.execute(f"DROP TABLE IF EXISTS {t}")
        self.conn.commit(); cur.close()
        self._run_sql_file("sql/07_audit_and_lineage_tables.sql")


if __name__ == "__main__":
    unittest.main()
