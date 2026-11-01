-- Check 1: row counts, source vs target.
-- Replace src_encounters / tgt_encounters with your tables.
SELECT
    (SELECT COUNT(*) FROM src_encounters) AS source_rows,
    (SELECT COUNT(*) FROM tgt_encounters) AS target_rows,
    (SELECT COUNT(*) FROM src_encounters) - (SELECT COUNT(*) FROM tgt_encounters) AS difference;
