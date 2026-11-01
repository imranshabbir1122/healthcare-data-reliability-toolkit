-- Check 4: business-level aggregates, overall and by group.
-- Overall totals.
SELECT
    (SELECT COALESCE(SUM(charge_amount), 0) FROM src_encounters) AS source_total,
    (SELECT COALESCE(SUM(charge_amount), 0) FROM tgt_encounters) AS target_total;

-- Totals by facility: shows WHERE a difference sits. Lists only groups that differ.
SELECT COALESCE(s.facility_code, t.facility_code) AS facility_code,
       COALESCE(s.total, 0) AS source_total,
       COALESCE(t.total, 0) AS target_total
FROM (SELECT facility_code, SUM(charge_amount) AS total FROM src_encounters GROUP BY facility_code) s
LEFT JOIN (SELECT facility_code, SUM(charge_amount) AS total FROM tgt_encounters GROUP BY facility_code) t
       ON s.facility_code = t.facility_code
WHERE ROUND(COALESCE(s.total, 0), 2) <> ROUND(COALESCE(t.total, 0), 2);
