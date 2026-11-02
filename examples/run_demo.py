"""End-to-end demo on synthetic data: reconcile, write audit rows, log lineage."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sample_data.make_sample_db import build  # noqa: E402
from toolkit import LineageLog, reconcile, write_results  # noqa: E402
from toolkit.reconcile import summarize  # noqa: E402

DB = "demo.db"
build(DB)
conn = sqlite3.connect(DB)

results = reconcile(
    conn,
    source="src_encounters",
    target="tgt_encounters",
    key_cols=["encounter_id"],
    compare_cols=["facility_code", "encounter_date", "charge_amount", "status", "updated_at"],
    numeric_cols=["charge_amount"],
)
print(summarize(results))
run_id = write_results(conn, results, "src_encounters", "tgt_encounters")
print(f"\nResults stored in recon_results (run_id={run_id})")

log = LineageLog(conn, run_id=run_id)
with log.step("load_encounters", "src_encounters", "tgt_encounters", "copy with type casting") as s:
    s.rows_in, s.rows_out = 200, 199
    s.note = "demo; reconciliation run " + run_id
print("\nLineage log:\n" + log.to_json())
conn.close()
