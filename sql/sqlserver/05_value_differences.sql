-- SQL Server (UNTESTED). Null-safe value comparison without IS DISTINCT FROM.
SELECT a.encounter_id,
       a.charge_amount AS source_amount, b.charge_amount AS target_amount,
       a.status AS source_status, b.status AS target_status
FROM src_encounters a
JOIN tgt_encounters b ON a.encounter_id = b.encounter_id
WHERE EXISTS (
    SELECT a.charge_amount, a.status, a.facility_code, a.encounter_date
    EXCEPT
    SELECT b.charge_amount, b.status, b.facility_code, b.encounter_date
);
