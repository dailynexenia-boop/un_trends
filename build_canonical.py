import csv
import json
from pathlib import Path
from datetime import datetime

from ingest.ingest_row import build_manual_entry
from utils.canonical_io import append_jsonl

from analysis.speaker_structure import build_speaker_structure
from analysis.micro_analysis import build_micro_analysis


# ==================================================
# PATHS
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
CANONICAL_DIR = BASE_DIR / "canonical"

CANONICAL_DIR.mkdir(exist_ok=True)
OUT_FILE = CANONICAL_DIR / "canonical.jsonl"


# ==================================================
# UTILS
# ==================================================

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


def normalize_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%B %d, %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


# ==================================================
# IDEMPOTENCE
# ==================================================

def load_existing_source_uids(path: Path) -> set:
    uids = set()
    if not path.exists():
        return uids

    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                uid = json.loads(line).get("source_uid")
                if uid:
                    uids.add(uid)
            except Exception:
                continue
    return uids


# ==================================================
# BUILD CANONICAL
# ==================================================

def build_canonical():
    csv_files = sorted(RAW_DIR.glob("*.csv"))

    if not csv_files:
        print("[WARN] No CSV files found")
        return

    existing_uids = load_existing_source_uids(OUT_FILE)

    added = skipped = failed = 0

    for csv_file in csv_files:
        print(f"[INFO] Processing {csv_file.name}")

        with open(csv_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for idx, row in enumerate(reader, start=1):
                source_uid = f"{csv_file.name}::{idx}"

                if source_uid in existing_uids:
                    skipped += 1
                    continue

                try:
                    raw_date = row.get("Date") or row.get("\ufeffDate")

                    entry = build_manual_entry(
                        date=datetime.fromisoformat(
                            normalize_date(raw_date)
                        ).date()
                        if raw_date
                        else None,
                        conference=clean(row.get("Conference")),
                        session_label=clean(row.get("Session")),
                        speaker_raw=clean(row.get("Country")),
                        signals_text=clean(row.get("Signals")),
                        keywords=split_list(row.get("Keywords")),
                    )

                    entry["source_uid"] = source_uid

                    # ----------------------------------
                    # DERIVED FIELDS (INITIAL COMPUTE)
                    # ----------------------------------
                    entry["speaker_structure"] = build_speaker_structure(entry)
                    entry["micro_analysis"] = build_micro_analysis(entry)

                    append_jsonl(OUT_FILE, entry)
                    existing_uids.add(source_uid)
                    added += 1

                except Exception as e:
                    failed += 1
                    print(f"[ERROR] {csv_file.name} row {idx}: {e}")

    print(
        f"[OK] Canonical build complete: "
        f"{added} added, {skipped} skipped, {failed} failed"
    )


# ==================================================
# CLI
# ==================================================

if __name__ == "__main__":
    build_canonical()
