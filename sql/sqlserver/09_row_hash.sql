-- SQL Server 2017+ (UNTESTED). Row-level hash comparison with explicit NULL markers.
SELECT a.encounter_id
FROM src_encounters a
JOIN tgt_encounters b ON a.encounter_id = b.encounter_id
WHERE HASHBYTES('SHA2_256', CONCAT_WS('|', COALESCE(a.facility_code, '<NULL>'), COALESCE(a.encounter_date, '<NULL>'),
                COALESCE(CAST(a.charge_amount AS VARCHAR(40)), '<NULL>'), COALESCE(a.status, '<NULL>'),
                COALESCE(a.updated_at, '<NULL>')))
   <> HASHBYTES('SHA2_256', CONCAT_WS('|', COALESCE(b.facility_code, '<NULL>'), COALESCE(b.encounter_date, '<NULL>'),
                COALESCE(CAST(b.charge_amount AS VARCHAR(40)), '<NULL>'), COALESCE(b.status, '<NULL>'),
                COALESCE(b.updated_at, '<NULL>')));
