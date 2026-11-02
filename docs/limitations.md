# Limitations

- **Early stage.** Tested only on the synthetic data in this repository. Not independently reviewed, certified, or used in production.
- **Not a compliance tool.** It does not assess HIPAA, USCDI, FHIR, HL7, or any other legal or standards requirement.
- **No clinical claims.** It checks data movement and consistency, not clinical correctness.
- **Databases.** Tested on SQLite and PostgreSQL 16 only. SQL Server files are untested drafts. Other DB-API drivers are untested. The shared `sql/05_value_differences.sql` uses SQLite's `IS NOT`; use the `sql/postgresql/` or `sql/sqlserver/` version elsewhere.
- **Lineage table.** The 0.3.0 `lineage_log` schema is not compatible with earlier tables.
- **NULL in unique rules.** Behavior depends on `null_policy`; pick the one that matches your database's constraint.
- **Performance.** The row-level hash runs in Python. For large tables push the hash into the database.
- **Timestamps.** Incremental checks compare timestamps as stored. Use one consistent format (ISO 8601) and one time zone.
- **Identifiers.** Table and column names are validated and then placed in SQL text. Never pass untrusted input as a name.
- **Scope.** Checks do not fix data. They report problems so a person can decide what to do.
- **Real data.** Do not load real patient data into the demos or tests. Follow your organization's privacy and security rules.
