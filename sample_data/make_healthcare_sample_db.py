"""Build a SYNTHETIC healthcare-shaped database with deliberate problems.

Everything here is invented: identifiers use "SYN-" prefixes, facility names are
generic, and codes are placeholders. There are no real patients, no real
organizations, and no real clinical content. Do not replace it with real data.

Tables
  facilities, patients, encounters, clinical_events, claims

Injected problems (exact counts, used by the tests)
  encounters.patient_id not in patients ............ 2 orphan encounters
  encounters.facility_code not in facilities ........ 1
  encounters discharge before admit ................. 2
  encounters with NULL admit_date ................... 1
  encounters.encounter_type outside agreed list ..... 2
  patients sharing one MRN .......................... 1 duplicated MRN
  clinical_events with no matching encounter ........ 3
  claims with no matching encounter ................. 2
  claims whose billed amount differs from charge .... 3
"""
import os
import random
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from toolkit.dialect import placeholders  # noqa: E402

random.seed(7)
TYPES = ["INPATIENT", "OUTPATIENT", "EMERGENCY"]


def build(path: str = "healthcare_sample.db") -> None:
    conn = sqlite3.connect(path)
    build_into(conn)
    conn.close()


def build_into(conn) -> None:
    """Create and fill the synthetic tables on any DB-API connection (SQLite, PostgreSQL)."""
    random.seed(7)
    cur = conn.cursor()

    def many(table, rows):
        marks = ",".join(placeholders(conn, len(rows[0])))
        cur.executemany(f"INSERT INTO {table} VALUES ({marks})", rows)

    for t in ("claims", "clinical_events", "encounters", "patients", "facilities"):
        cur.execute(f"DROP TABLE IF EXISTS {t}")
    cur.execute("CREATE TABLE facilities (facility_code VARCHAR(20), facility_name VARCHAR(100), setting VARCHAR(20))")
    cur.execute("CREATE TABLE patients (patient_id VARCHAR(20), mrn VARCHAR(20), birth_year INTEGER, sex VARCHAR(1))")
    cur.execute("""CREATE TABLE encounters (encounter_id INTEGER, patient_id VARCHAR(20), facility_code VARCHAR(20),
        admit_date VARCHAR(10), discharge_date VARCHAR(10), encounter_type VARCHAR(20), charge_amount NUMERIC(12,2))""")
    cur.execute("""CREATE TABLE clinical_events (event_id INTEGER, encounter_id INTEGER,
        event_type VARCHAR(20), code VARCHAR(20), event_ts VARCHAR(30))""")
    cur.execute("CREATE TABLE claims (claim_id VARCHAR(20), encounter_id INTEGER, billed_amount NUMERIC(12,2), claim_status VARCHAR(20))")

    many("facilities", [
        ("FAC01", "Synthetic Rural Clinic A", "clinic"),
        ("FAC02", "Synthetic Community Hospital B", "hospital"),
        ("FAC03", "Synthetic Critical Access Hospital C", "hospital")])

    patients = [(f"SYN-P{i:04d}", f"MRN{100000 + i}", random.randint(1940, 2020), random.choice("MF"))
                for i in range(1, 101)]
    patients.append(("SYN-P0101", patients[9][1], 1975, "F"))        # duplicated MRN
    many("patients", patients)

    enc = []
    for i in range(1, 301):
        day = random.randint(1, 25)
        admit = f"2026-{random.randint(1, 9):02d}-{day:02d}"
        disch = f"2026-{admit[5:7]}-{day + random.randint(0, 3):02d}"
        enc.append([i, f"SYN-P{random.randint(1, 100):04d}", random.choice(["FAC01", "FAC02", "FAC03"]),
                    admit, disch, random.choice(TYPES), round(random.uniform(80, 4000), 2)])
    enc[4][1] = "SYN-P9999"; enc[5][1] = "SYN-P9998"           # 2 orphan encounters
    enc[10][2] = "FAC99"                                        # 1 unknown facility
    enc[20][4] = "2026-01-01"; enc[21][4] = "2026-01-02"        # 2 discharge before admit
    enc[30][3] = None                                           # 1 null admit
    enc[40][5] = "INPT"; enc[41][5] = "ER"                      # 2 bad types
    many("encounters", [tuple(r) for r in enc])

    events = []
    for i in range(1, 601):
        events.append((i, random.randint(1, 300), random.choice(["VITAL", "LAB", "DIAGNOSIS"]),
                       f"SYN-{random.randint(1, 40):03d}", f"2026-0{random.randint(1, 9)}-10T08:00:00"))
    events[0] = (1, 9001, "VITAL", "SYN-001", "2026-01-10T08:00:00")       # 3 orphan events
    events[1] = (2, 9002, "LAB", "SYN-002", "2026-01-10T08:00:00")
    events[2] = (3, 9003, "LAB", "SYN-003", "2026-01-10T08:00:00")
    many("clinical_events", events)

    claims = [(f"CLM{i:05d}", e[0], e[6], random.choice(["SUBMITTED", "PAID", "DENIED"]))
              for i, e in enumerate(enc[:250], start=1)]
    for idx in (100, 101, 102):                                 # 3 amount mismatches
        c = list(claims[idx]); c[2] = round(c[2] + 37.5, 2); claims[idx] = tuple(c)
    claims.append(("CLM90001", 9101, 120.0, "SUBMITTED"))       # 2 orphan claims
    claims.append(("CLM90002", 9102, 80.0, "PAID"))
    many("claims", claims)
    conn.commit()
    cur.close()


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "healthcare_sample.db")
    print("synthetic healthcare sample database created")
