# SQL Server examples (UNTESTED)

These are drafts written from SQL Server documentation. **They have not been run against a SQL Server instance** in this project. Test them on a non-production database and adjust before relying on them. Only SQLite and PostgreSQL 16 are covered by the test suite.

Main differences from the files in `sql/`:

| Topic | SQL Server |
|---|---|
| Null-safe compare | `EXISTS (SELECT a.x EXCEPT SELECT b.x)` (works on all versions); `IS DISTINCT FROM` needs SQL Server 2022 |
| Hash | `HASHBYTES('SHA2_256', ...)` and `CONCAT_WS` (2017+) |
| Create if missing | No `IF NOT EXISTS` on `CREATE TABLE`; use `IF OBJECT_ID(...) IS NULL` |
| `UNIQUE` and NULL | A unique constraint treats NULLs as equal; use `null_policy="strict"` in `rules.unique` to match |
| Python driver | `pyodbc` uses `?` placeholders, which the toolkit already supports; untested |
