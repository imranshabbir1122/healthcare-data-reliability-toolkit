# Healthcare Data Reliability Toolkit (v0.1.0, first release)

An open, vendor-neutral set of templates for checking that data arrives complete, consistent and traceable after it is moved or transformed. It is aimed at small, rural and community healthcare organizations that receive standardized data but may not have a large in-house data-engineering team.

> **Status: first release.** It has been tested only on the synthetic sample data included here. It has not been independently reviewed, certified, or used in production. Review and adapt it before using it with real data.

## What is included

| Folder | Contents |
|---|---|
| `toolkit/` | Python module: source-to-target reconciliation checks (`reconcile.py`) and a lineage log (`lineage.py`) |
| `sql/` | Plain SQL templates for row counts, key checks, null checks, aggregates, value differences, incremental (watermark) checks, audit and lineage tables |
| `docs/` | Validation checklist, lineage record template, legacy-to-cloud migration checklist |
| `sample_data/` | Script that builds a **synthetic** demo database with deliberate problems |
| `examples/` | A demo that runs everything end to end |
| `tests/` | Unit tests |

## Quick start

Requires Python 3.9 or newer. No packages to install.

```bash
python examples/run_demo.py     # reconciles the sample data and prints the results
python -m unittest discover -s tests
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

1. Row counts 2. Duplicate keys 3. Missing and extra keys 4. Null counts per column 5. Business totals 6. Row-level value comparison (hash)

## Limits

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
