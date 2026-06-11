import csv
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

# -----------------------------
# PATHS
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
CANONICAL_DIR = BASE_DIR / "canonical"
LOG_DIR = BASE_DIR / "logs"

RAW_DIR.mkdir(exist_ok=True)
CANONICAL_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# -----------------------------
# COLUMN MAP (SOURCE OF TRUTH)
# -----------------------------
COLUMN_MAP = {
    "date": ["Date"],
    "conference": ["Conference"],
    "session": ["Session"],
    "country": ["Country"],
    "country_group": ["Groupe of Country"],
    "signals_text": ["Signals"],
    "keywords": ["Keywords"]
}

# -----------------------------
# UTILS
# -----------------------------
def clean(value):
    if value is None:
        return None
    v = str(value).strip()
    return v if v else None

def split_list(value):
    if not value:
        return []
    for sep in [";", ","]:
        if sep in value:
            return [v.strip() for v in value.split(sep) if v.strip()]
    return [value.strip()]

def get_value(row, keys):
    for k in keys:
        if k in row and clean(row[k]):
            return row[k]
    return None

def normalize_date(value):
    try:
        return datetime.strptime(value, "%B %d, %Y").date().isoformat()
    except Exception:
        return None

# -----------------------------
# INGESTION
# -----------------------------
def ingest_csv(csv_file: Path, session_id: str):
    timestamp = datetime.now(timezone.utc).isoformat()
    canonical_file = CANONICAL_DIR / f"{session_id}_entries.jsonl"
    log_file = LOG_DIR / f"ingestion_{session_id}.log"

    rows_read = 0

    with open(csv_file, newline="", encoding="utf-8") as f, \
         open(canonical_file, "w", encoding="utf-8") as out:

        reader = csv.DictReader(f)

        for idx, row in enumerate(reader, start=1):
            rows_read += 1

            entry = {
                # ---- audit
                "entry_id": str(uuid.uuid4()),
                "session_id": session_id,
                "source_file": csv_file.name,
                "row_number": idx,
                "ingested_at": timestamp,

                # ---- context
                "date": normalize_date(get_value(row, COLUMN_MAP["date"])),
                "conference": get_value(row, COLUMN_MAP["conference"]),
                "session_label": get_value(row, COLUMN_MAP["session"]),

                # ---- actor
                "country": get_value(row, COLUMN_MAP["country"]),
                "country_group": get_value(row, COLUMN_MAP["country_group"]),

                # ---- CORE CONTENT (CRITICAL)
                "signals_text": clean(get_value(row, COLUMN_MAP["signals_text"])),

                # ---- analyst annotations
                "keywords": split_list(get_value(row, COLUMN_MAP["keywords"]))
            }

            out.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with open(log_file, "w", encoding="utf-8") as log:
        log.write(
            f"File: {csv_file.name}\n"
            f"Session: {session_id}\n"
            f"Rows read: {rows_read}\n"
            f"Timestamp: {timestamp}\n"
        )

    print(f"[OK] Ingested {rows_read} rows from {csv_file.name}")

# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python ingest_block0.py <csv_filename> <session_id>")
        sys.exit(1)

    ingest_csv(RAW_DIR / sys.argv[1], sys.argv[2])
