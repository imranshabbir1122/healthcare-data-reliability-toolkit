"""Create a SYNTHETIC demo database with deliberate source-to-target problems.

All data here is invented. It contains no real patients or organizations.
"""
import random
import sqlite3
import sys

random.seed(42)


def build(path: str = "sample.db") -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    for t in ("src_encounters", "tgt_encounters"):
        cur.execute(f"DROP TABLE IF EXISTS {t}")
        cur.execute(f"""CREATE TABLE {t} (
            encounter_id INTEGER, facility_code TEXT, encounter_date TEXT,
            charge_amount REAL, status TEXT, updated_at TEXT)""")
    facilities = ["F01", "F02", "F03"]
    statuses = ["OPEN", "CLOSED", "BILLED"]
    rows = []
    for i in range(1, 201):
        rows.append((i, random.choice(facilities), f"2026-{random.randint(1, 9):02d}-{random.randint(1, 28):02d}",
                     round(random.uniform(50, 2500), 2), random.choice(statuses),
                     f"2026-10-{random.randint(1, 28):02d}"))
    cur.executemany("INSERT INTO src_encounters VALUES (?,?,?,?,?,?)", rows)

    tgt = [list(r) for r in rows]
    # deliberate problems
    tgt = [r for r in tgt if r[0] not in (10, 55, 120)]          # 3 rows missing
    tgt.append([999, "F02", "2026-09-09", 100.0, "OPEN", "2026-10-02"])  # 1 extra row
    tgt.append(list(tgt[5]))                                      # 1 duplicate key
    tgt[20][4] = None                                             # null status
    tgt[40][4] = None                                             # null status
    tgt[60][3] = round(tgt[60][3] + 25.0, 2)                      # changed amount
    tgt[80][3] = round(tgt[80][3] - 10.5, 2)                      # changed amount
    cur.executemany("INSERT INTO tgt_encounters VALUES (?,?,?,?,?,?)", [tuple(r) for r in tgt])
    conn.commit()
    conn.close()


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "sample.db")
    print("sample database created")
