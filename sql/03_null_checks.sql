-- Check 3: null counts per column, source vs target.
-- Add one line per column you want to compare.
SELECT 'status' AS column_name,
       (SELECT COUNT(*) FROM src_encounters WHERE status IS NULL) AS source_nulls,
       (SELECT COUNT(*) FROM tgt_encounters WHERE status IS NULL) AS target_nulls
UNION ALL
SELECT 'facility_code',
       (SELECT COUNT(*) FROM src_encounters WHERE facility_code IS NULL),
       (SELECT COUNT(*) FROM tgt_encounters WHERE facility_code IS NULL)
UNION ALL
SELECT 'charge_amount',
       (SELECT COUNT(*) FROM src_encounters WHERE charge_amount IS NULL),
       (SELECT COUNT(*) FROM tgt_encounters WHERE charge_amount IS NULL);
