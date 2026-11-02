-- PostgreSQL. Changed rows since the last watermark, and a watermark table.
SELECT
    (SELECT COUNT(*) FROM src_encounters WHERE updated_at > '2026-10-15') AS source_changed_rows,
    (SELECT COUNT(*) FROM tgt_encounters WHERE updated_at > '2026-10-15') AS target_changed_rows;

CREATE TABLE IF NOT EXISTS load_watermark (
    table_name VARCHAR(255) PRIMARY KEY,
    last_successful_value VARCHAR(40),
    updated_at VARCHAR(40)
);

-- Late-arriving rows: in the source at or before the watermark but missing from the target.
SELECT a.encounter_id
FROM src_encounters a
LEFT JOIN tgt_encounters b ON a.encounter_id = b.encounter_id
WHERE b.encounter_id IS NULL
  AND a.updated_at <= (SELECT MAX(updated_at) FROM tgt_encounters);
