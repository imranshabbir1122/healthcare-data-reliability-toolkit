-- PostgreSQL. Row-level hash comparison; NULLs are made explicit so a NULL cannot collide with a value.
-- Keys duplicated on either side are not skipped here, unlike the Python module.
SELECT a.encounter_id
FROM src_encounters a
JOIN tgt_encounters b ON a.encounter_id = b.encounter_id
WHERE md5(concat_ws('|', COALESCE(a.facility_code, '<NULL>'), COALESCE(a.encounter_date, '<NULL>'),
                    COALESCE(a.charge_amount::text, '<NULL>'), COALESCE(a.status, '<NULL>'),
                    COALESCE(a.updated_at, '<NULL>')))
   <> md5(concat_ws('|', COALESCE(b.facility_code, '<NULL>'), COALESCE(b.encounter_date, '<NULL>'),
                    COALESCE(b.charge_amount::text, '<NULL>'), COALESCE(b.status, '<NULL>'),
                    COALESCE(b.updated_at, '<NULL>')));
