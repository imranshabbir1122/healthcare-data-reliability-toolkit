# Validation checklist

Use before sign-off on any source-to-target load or migration. Mark each item with the evidence (query, report, or screenshot).

## Structure
- [ ] Row counts match, or every difference is explained
- [ ] Column names and data types match the mapping document
- [ ] Primary and business keys are unique in source and target

## Integrity
- [ ] No keys missing from the target
- [ ] No unexpected keys in the target
- [ ] Null counts match per column, or differences are documented
- [ ] Referential integrity holds (child rows have a parent)
- [ ] Row-level comparison (value or hash) shows no unexplained differences

## Business results
- [ ] Totals match for key measures (amounts, counts)
- [ ] Group-level totals match (by facility, period, status)
- [ ] A business owner has reviewed sample records

## Incremental loads
- [ ] Watermark moves forward only after checks pass
- [ ] Late-arriving and updated records are handled
- [ ] Re-running the load does not create duplicates

## Operations
- [ ] Failures raise an alert and are logged
- [ ] Results are stored in an audit table
- [ ] Lineage is recorded for the step (see lineage_template.md)

## Healthcare data care
- [ ] Testing uses de-identified or synthetic data where possible
- [ ] Access to real data follows the organization's privacy and security rules
- [ ] This checklist is a technical aid, not a compliance assessment
