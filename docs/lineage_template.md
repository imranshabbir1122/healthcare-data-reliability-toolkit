# Lineage record template

Fill in one record per dataset or processing step. The `LineageLog` class in `toolkit/lineage.py` stores the same fields in a table.

| Field | Description | Example |
|---|---|---|
| Step name | Short name of the process | load_encounters |
| Source | System, table or file read | src_encounters |
| Target | Table or file written | tgt_encounters |
| Transformation | Rule applied, in plain words | cast dates, trim text, drop test records |
| Business definition | What a key field means | status: current billing state |
| Run time | When it ran | 2026-11-02T10:00:00Z |
| Rows in / out | Counts before and after | 200 / 199 |
| Owner | Person or team responsible | Data engineering |
| Change history | Version of the code or config | v0.1.0 |
| Notes | Known limits or exceptions | 1 row rejected: null key |

## Tips
- Record rejected rows and the reason, not only successful ones.
- Keep one definition per field and link to it.
- Review lineage whenever a source schema changes.
