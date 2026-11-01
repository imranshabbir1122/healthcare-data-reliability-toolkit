-- Check 6: incremental (watermark) reconciliation.
-- After each incremental load, compare only rows changed since the last successful
-- watermark. Replace '2026-10-15' with the stored watermark value.
SELECT
    (SELECT COUNT(*) FROM src_encounters WHERE updated_at > '2026-10-15') AS source_changed_rows,
    (SELECT COUNT(*) FROM tgt_encounters WHERE updated_at > '2026-10-15') AS target_changed_rows;

-- Store the new watermark only after the checks pass.
-- (Example table; adapt to your orchestration tool.)
CREATE TABLE IF NOT EXISTS load_watermark (
    table_name TEXT PRIMARY KEY,
    last_successful_value TEXT,
    updated_at TEXT
);
