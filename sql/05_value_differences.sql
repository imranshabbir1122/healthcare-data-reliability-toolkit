-- Check 5: rows whose key matches but whose values differ.
-- Portable version: compare columns directly. Uses IS NOT for null-safe comparison
-- in SQLite; in other databases use IS DISTINCT FROM (PostgreSQL, Snowflake) or
-- an equivalent null-safe expression.
SELECT a.encounter_id,
       a.charge_amount AS source_amount, b.charge_amount AS target_amount,
       a.status AS source_status, b.status AS target_status
FROM src_encounters a
JOIN tgt_encounters b ON a.encounter_id = b.encounter_id
WHERE a.charge_amount IS NOT b.charge_amount
   OR a.status IS NOT b.status
   OR a.facility_code IS NOT b.facility_code
   OR a.encounter_date IS NOT b.encounter_date;
