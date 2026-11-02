# Synthetic healthcare scenarios

`sample_data/make_healthcare_sample_db.py` builds a small database with five tables: `facilities`, `patients`, `encounters`, `clinical_events`, `claims`. **All data is invented** (identifiers use `SYN-`, facility names are generic, codes are placeholders). Never replace it with real patient data.

Run it:

```bash
python examples/run_healthcare_demo.py
```

| Scenario | Rule | Injected problems |
|---|---|---|
| Encounter points to a patient that does not exist | `referential_integrity` | 2 |
| Encounter points to an unknown facility | `referential_integrity` | 1 |
| Discharge date before admit date | `date_order` | 2 |
| Encounter with no admit date | `not_null` | 1 |
| Encounter type outside the agreed list | `allowed_values` | 2 |
| Two patient records share one medical record number | `unique` | 1 |
| Clinical event with no matching encounter | `referential_integrity` | 3 |
| Claim with no matching encounter | `referential_integrity` | 2 |
| Claim billed amount differs from encounter charge | `amount_matches_parent` | 3 |

The tests assert these exact counts, so a change that stops a rule from detecting a problem fails the test run.

These scenarios illustrate the kinds of failures the checks look for. They do not represent any real organization's data quality.
