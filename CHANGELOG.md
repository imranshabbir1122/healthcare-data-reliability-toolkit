# Changelog

## 0.3.0
- `rules.unique`: defined NULL behavior for single and composite keys. `null_policy="ignore"` (default; rows with any NULL are not duplicates, as in the SQL standard, PostgreSQL and SQLite) or `"strict"` (NULLs equal, as in a SQL Server UNIQUE constraint). Check names now include the policy. Tested.
- `check_incremental`: always returns the same set of checks. With an empty target it now reports pending source rows and null timestamps, like a loaded target does.
- Portability: new `dialect` module detects the driver's placeholder style (`?`, `%s`, named, numeric). Audit and lineage DDL is now portable (no AUTOINCREMENT, no `IF NOT EXISTS`). `Decimal` values hash like floats and ints. Sample databases build on SQLite or PostgreSQL.
- Tested on SQLite and PostgreSQL 16 (psycopg2). `sql/postgresql/` holds tested PostgreSQL versions of the dialect-specific queries. `sql/sqlserver/` holds drafts that are **untested**.
- `LineageLog` (breaking schema change): added `run_id`, `seq`, `status`, `error_detail`, `duration_ms`, `toolkit_version`; new `step()` context manager that records FAILED steps with the error and re-raises; `to_json()` returns one run by default. A `lineage_log` table from 0.1.x or 0.2.x must be dropped or migrated by hand.
- Tests: 44 (7 are PostgreSQL integration tests that run only when `TOOLKIT_PG_DSN` is set and psycopg2 is installed). Added integration tests for a full run (rules, audit, lineage), lineage failure paths, dialect handling, rule edge cases.

## 0.2.0
- `reconcile`: NULL-key reporting, safe handling of duplicate keys in the row-level check, numeric tolerance for totals, normalized number hashing, optional text normalization, empty-table handling, composite-key tests.
- New `incremental.check_incremental`: null timestamps, late-arriving rows missed by a watermark, target ahead of source, pending rows (informational).
- New `rules` module: not-null, unique, allowed values, referential integrity, date order, amount-matches-parent.
- New synthetic healthcare dataset (facilities, patients, encounters, clinical events, claims) with documented injected problems, plus `examples/run_healthcare_demo.py`.
- New docs: reference architecture (with diagram), scenarios, limitations.
- Tests: 19 passing (was 4).

## 0.1.0
- First release: reconciliation checks, lineage log, SQL templates, checklists, synthetic demo.
