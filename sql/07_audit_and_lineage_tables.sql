-- Audit and lineage tables. The Python module creates these automatically; use this
-- file if you want to create them yourself. Same columns as toolkit 0.3.0.
-- Add IF NOT EXISTS on SQLite, PostgreSQL and MySQL. On SQL Server see sql/sqlserver/.

CREATE TABLE recon_results (
    run_id VARCHAR(64), run_ts VARCHAR(40), source_table VARCHAR(255), target_table VARCHAR(255),
    check_name VARCHAR(255), status VARCHAR(16), source_value VARCHAR(255),
    target_value VARCHAR(255), detail VARCHAR(4000)
);

-- One row per processing step. status: SUCCESS, FAILED, WARNING, SKIPPED.
CREATE TABLE lineage_log (
    step_id VARCHAR(40), run_id VARCHAR(64), seq INTEGER, step_ts VARCHAR(40),
    step_name VARCHAR(255), source VARCHAR(255), target VARCHAR(255),
    transformation VARCHAR(1000), rows_in INTEGER, rows_out INTEGER,
    status VARCHAR(16), error_detail VARCHAR(2000), duration_ms INTEGER,
    toolkit_version VARCHAR(16), note VARCHAR(2000)
);

-- Example: latest failed checks.
SELECT run_id, check_name, source_value, target_value, detail
FROM recon_results
WHERE status = 'FAIL'
ORDER BY run_ts DESC;

-- Example: failed pipeline steps with the error text.
SELECT run_id, seq, step_name, error_detail
FROM lineage_log
WHERE status = 'FAILED'
ORDER BY step_ts DESC;
