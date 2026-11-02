"""Run integrity rules on the SYNTHETIC healthcare sample and log the run."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sample_data.make_healthcare_sample_db import build  # noqa: E402
from toolkit import LineageLog, rules, write_results  # noqa: E402
from toolkit.reconcile import summarize  # noqa: E402

DB = "healthcare_demo.db"
build(DB)
conn = sqlite3.connect(DB)

results = [
    rules.not_null(conn, "encounters", "admit_date"),
    rules.unique(conn, "patients", ["mrn"]),
    rules.allowed_values(conn, "encounters", "encounter_type", ["INPATIENT", "OUTPATIENT", "EMERGENCY"]),
    rules.referential_integrity(conn, "encounters", "patient_id", "patients", "patient_id"),
    rules.referential_integrity(conn, "encounters", "facility_code", "facilities", "facility_code"),
    rules.referential_integrity(conn, "clinical_events", "encounter_id", "encounters", "encounter_id"),
    rules.referential_integrity(conn, "claims", "encounter_id", "encounters", "encounter_id"),
    rules.date_order(conn, "encounters", "admit_date", "discharge_date"),
    rules.amount_matches_parent(conn, "claims", "encounter_id", "billed_amount",
                                "encounters", "encounter_id", "charge_amount"),
]
print(summarize(results))
run_id = write_results(conn, results, "healthcare_sample", "integrity_rules")
with LineageLog(conn, run_id=run_id).step("integrity_rules", "healthcare_sample", "recon_results",
                                          "rule checks, no data changed") as s:
    s.rows_out = len(results)
print(f"\nStored in recon_results (run_id={run_id}). Synthetic data only.")
conn.close()
