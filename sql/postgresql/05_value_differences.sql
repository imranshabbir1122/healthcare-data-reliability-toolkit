-- PostgreSQL. Rows whose key matches but whose values differ (null-safe).
SELECT a.encounter_id,
       a.charge_amount AS source_amount, b.charge_amount AS target_amount,
       a.status AS source_status, b.status AS target_status
FROM src_encounters a
JOIN tgt_encounters b ON a.encounter_id = b.encounter_id
WHERE a.charge_amount IS DISTINCT FROM b.charge_amount
   OR a.status IS DISTINCT FROM b.status
   OR a.facility_code IS DISTINCT FROM b.facility_code
   OR a.encounter_date IS DISTINCT FROM b.encounter_date;
