# Healthcare Data Reliability Toolkit (v0.3.1)

An open, vendor-neutral set of templates for checking that data arrives complete, consistent and traceable after it is moved or transformed. It is aimed at small, rural and community healthcare organizations that receive standardized data but may not have a large in-house data-engineering team.

> **Status: early release.** It has been tested only on the synthetic sample data included here, on SQLite and PostgreSQL 16. SQL Server examples are provided but untested. It has not been independently reviewed, certified, or used in production. Review and adapt it before using it with real data.

## What is included

| Folder | Contents |
|---|---|
| `toolkit/` | Python modules: source-to-target reconciliation (`reconcile.py`), incremental-load validation (`incremental.py`), integrity rules (`rules.py`), lineage log (`lineage.py`) |
| `sql/` | Plain SQL templates for row counts, key checks, null checks, aggregates, value differences, incremental (watermark) checks, audit and lineage tables |
| `docs/` | Reference architecture (with diagram), synthetic scenarios, limitations, validation checklist, lineage template, migration checklist |
| `sample_data/` | Scripts that build **synthetic** demo databases with deliberate problems, including a healthcare-shaped one (encounters, patients, facilities, clinical events, claims) |
| `examples/` | Two demos: reconciliation (`run_demo.py`) and healthcare integrity rules (`run_healthcare_demo.py`) |
| `tests/` | Unit tests |

## Quick start

Requires Python 3.9 or newer. No packages to install for SQLite. For PostgreSQL install `psycopg2` yourself.

```bash
python examples/run_demo.py             # reconciliation on a synthetic table pair
python examples/run_healthcare_demo.py  # integrity rules on synthetic healthcare tables
python -m unittest discover -s tests
```

PostgreSQL integration tests (use a throwaway database; they create and drop the sample tables):

```bash
TOOLKIT_PG_DSN="host=localhost dbname=scratch user=me" python -m unittest tests.test_postgres
```

The demo builds two small synthetic tables. The target table has been altered on purpose (3 rows missing, 1 extra, 1 duplicate key, 2 null values, 2 changed amounts) so you can see each check detect a problem. The row-level comparison reports 4 rows: the 2 changed amounts and the 2 rows with a null status.

## Using it on your own tables

```python
import sqlite3
from toolkit import reconcile, write_results
from toolkit.reconcile import summarize

conn = sqlite3.connect("your.db")     # any DB-API 2.0 connection
results = reconcile(
    conn, source="src_table", target="tgt_table",
    key_cols=["id"], compare_cols=["col_a", "col_b"], numeric_cols=["amount"],
)
print(summarize(results))
write_results(conn, results, "src_table", "tgt_table")   # stores an audit trail
```

The SQL files in `sql/` do the same checks and can be run directly in your database. Some syntax (null-safe comparison, hash functions) differs by database; the comments say where.

## Checks

- **Reconciliation:** row counts, duplicate keys, NULL keys, missing and extra keys, null counts, totals (with tolerance), row-level value comparison (hash).
- **Incremental loads:** null timestamps, late-arriving rows a watermark would skip, target ahead of source, pending rows (informational).
- **Integrity rules:** not null, unique, allowed values, referential integrity, date order, claim amount vs encounter charge.

See `docs/reference_architecture.md` for where each check fits in a pipeline, and `docs/scenarios.md` for the synthetic healthcare scenarios.

## Databases

| Database | Status |
|---|---|
| SQLite | Tested (standard library) |
| PostgreSQL 16 | Tested with psycopg2; `sql/postgresql/` |
| SQL Server | Drafts in `sql/sqlserver/`, **untested** |
| Others | Should work through any DB-API 2.0 driver, untested |

The toolkit reads the driver's `paramstyle`, so `?` and `%s` drivers both work.

## Run log

```python
from toolkit import LineageLog
log = LineageLog(conn, run_id=run_id)
with log.step("load_encounters", "raw.enc", "curated.enc", "dedupe + cast") as s:
    ...                       # your work
    s.rows_in, s.rows_out = 200, 199
# a failure is recorded as FAILED with the error text, then re-raised
```

## Limits

See `docs/limitations.md` for the full list. In short:

- Not a compliance tool. It does not assess HIPAA or any other legal requirement.
- Do not load real patient data into the demo or tests. Use de-identified or synthetic data and follow your organization's privacy and security rules.
- Names of tables and columns are validated but placed in SQL text. Do not pass untrusted input as a name.
- The row-level hash runs in Python for portability and is slow on very large tables. Push it into SQL for large volumes.
- Alignment with national data standards (for example USCDI) is not claimed or implemented. The toolkit supports the data checking that organizations do after exchange.

## Contributing and feedback

Issues and suggestions are welcome. If you use it, please share what worked and what did not.

## License

MIT. See `LICENSE`.

## Author

Imran Shabbir, data engineer.
