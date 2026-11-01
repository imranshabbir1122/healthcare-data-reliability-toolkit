-- Audit table for reconciliation results (the Python module writes the same shape).
CREATE TABLE IF NOT EXISTS recon_results (
    run_id TEXT, run_ts TEXT, source_table TEXT, target_table TEXT,
    check_name TEXT, status TEXT, source_value TEXT, target_value TEXT, detail TEXT
);

-- Lineage log: one row per processing step.
CREATE TABLE IF NOT EXISTS lineage_log (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    step_ts TEXT, step_name TEXT, source TEXT, target TEXT,
    transformation TEXT, rows_in INTEGER, rows_out INTEGER, note TEXT
);

-- Example: latest failed checks.
SELECT run_id, check_name, source_value, target_value, detail
FROM recon_results
WHERE status = 'FAIL'
ORDER BY run_ts DESC;
