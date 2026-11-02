-- Integrity rules for the synthetic healthcare sample (standard SQL; check dialect notes).
-- Each query returns the violating rows. Zero rows means the rule passes.

-- Orphan child rows (encounters without a patient)
SELECT e.encounter_id, e.patient_id
FROM encounters e LEFT JOIN patients p ON e.patient_id = p.patient_id
WHERE e.patient_id IS NOT NULL AND p.patient_id IS NULL;

-- Discharge before admit (ISO 8601 text dates)
SELECT encounter_id, admit_date, discharge_date
FROM encounters
WHERE admit_date IS NOT NULL AND discharge_date IS NOT NULL AND discharge_date < admit_date;

-- Duplicate medical record numbers
SELECT mrn, COUNT(*) FROM patients GROUP BY mrn HAVING COUNT(*) > 1;

-- Values outside the agreed list
SELECT encounter_type, COUNT(*) FROM encounters
WHERE encounter_type NOT IN ('INPATIENT', 'OUTPATIENT', 'EMERGENCY')
GROUP BY encounter_type;

-- Claim amount disagrees with encounter charge (tolerance 0.005)
SELECT c.claim_id, c.billed_amount, e.charge_amount
FROM claims c JOIN encounters e ON c.encounter_id = e.encounter_id
WHERE ABS(COALESCE(c.billed_amount, 0) - COALESCE(e.charge_amount, 0)) > 0.005;
