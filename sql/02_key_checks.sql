-- Check 2: duplicate keys, missing keys, extra keys.
-- Key column here: encounter_id. For composite keys, add columns to the joins and GROUP BY.

-- 2a. Duplicate keys in the target (run again against the source).
SELECT encounter_id, COUNT(*) AS occurrences
FROM tgt_encounters
GROUP BY encounter_id
HAVING COUNT(*) > 1;

-- 2b. Keys in the source that are missing from the target.
SELECT a.encounter_id
FROM src_encounters a
LEFT JOIN tgt_encounters b ON a.encounter_id = b.encounter_id
WHERE b.encounter_id IS NULL;

-- 2c. Keys in the target that are not in the source.
SELECT b.encounter_id
FROM tgt_encounters b
LEFT JOIN src_encounters a ON a.encounter_id = b.encounter_id
WHERE a.encounter_id IS NULL;
