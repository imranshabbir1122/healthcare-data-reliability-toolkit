# Legacy-to-cloud migration checklist

## 1. Assess
- [ ] Inventory source systems, tables, owners, and refresh schedules
- [ ] Map data flows and downstream consumers
- [ ] Note known quality problems in the source
- [ ] Define acceptance criteria and baselines (load time, failure rate, onboarding time)

## 2. Build
- [ ] Create the target model and mapping document
- [ ] Build the load with logging and audit tables
- [ ] Add reconciliation checks (see validation_checklist.md)

## 3. Validate in parallel
- [ ] Run old and new processes side by side
- [ ] Compare outputs and explain every difference
- [ ] Get written business sign-off

## 4. Cut over
- [ ] Agree a cutover window and freeze changes in the source
- [ ] Run the final load and the full reconciliation
- [ ] Confirm monitoring and alerts are active

## 5. Roll back if needed
- [ ] Define rollback triggers before cutover (for example: reconciliation fails, key report wrong)
- [ ] Keep the legacy process available until the target is stable
- [ ] Document the rollback steps and who decides

## 6. Retire
- [ ] Retire the legacy process only after an agreed stability period
- [ ] Archive documentation, lineage, and reconciliation results
- [ ] Record lessons learned and update this checklist
