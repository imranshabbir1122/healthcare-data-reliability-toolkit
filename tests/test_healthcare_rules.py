import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sample_data.make_healthcare_sample_db import build  # noqa: E402
from toolkit import rules  # noqa: E402


class HealthcareRules(unittest.TestCase):
    def setUp(self):
        self.path = "test_hc_tmp.db"
        build(self.path)
        self.c = sqlite3.connect(self.path)

    def tearDown(self):
        self.c.close()
        os.remove(self.path)

    def n(self, res):
        return int(res.target_value)

    def test_injected_counts(self):
        c = self.c
        self.assertEqual(self.n(rules.referential_integrity(c, "encounters", "patient_id", "patients", "patient_id")), 2)
        self.assertEqual(self.n(rules.referential_integrity(c, "encounters", "facility_code", "facilities", "facility_code")), 1)
        self.assertEqual(self.n(rules.date_order(c, "encounters", "admit_date", "discharge_date")), 2)
        self.assertEqual(self.n(rules.not_null(c, "encounters", "admit_date")), 1)
        self.assertEqual(self.n(rules.allowed_values(c, "encounters", "encounter_type",
                                                     ["INPATIENT", "OUTPATIENT", "EMERGENCY"])), 2)
        self.assertEqual(self.n(rules.unique(c, "patients", ["mrn"])), 1)
        self.assertEqual(self.n(rules.referential_integrity(c, "clinical_events", "encounter_id", "encounters", "encounter_id")), 3)
        self.assertEqual(self.n(rules.referential_integrity(c, "claims", "encounter_id", "encounters", "encounter_id")), 2)
        self.assertEqual(self.n(rules.amount_matches_parent(c, "claims", "encounter_id", "billed_amount",
                                                            "encounters", "encounter_id", "charge_amount")), 3)

    def test_clean_rule_passes(self):
        self.assertEqual(rules.unique(self.c, "patients", ["patient_id"]).status, "PASS")
        self.assertEqual(rules.not_null(self.c, "patients", "patient_id").status, "PASS")

    def test_unsafe_identifier_rejected(self):
        with self.assertRaises(ValueError):
            rules.not_null(self.c, "encounters; DROP TABLE x", "admit_date")


if __name__ == "__main__":
    unittest.main()
