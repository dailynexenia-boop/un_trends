from ingest.enrich_entry import enrich_entry
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from analysis.speaker_structure import build_speaker_structure
from analysis.micro_analysis import build_micro_analysis


# ==================================================
# KEYWORDS NORMALIZATION (Notion-style, minimal)
# ==================================================

def normalize_keywords(raw: List[str]) -> List[str]:
    """
    Minimal normalization:
    - strip
    - deduplicate (case-insensitive)
    - preserve original casing of first occurrence
    """
    cleaned = []
    seen = set()

    for k in raw or []:
        k2 = k.strip()
        if not k2:
            continue

        key = k2.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(k2)

    return cleaned


# ==================================================
# CORE INGEST (MANUAL ENTRY)
# ==================================================

def ingest_manual_entry(entry: Dict) -> Dict:
    """
    Apply the same analytical pipeline as CSV build,
    on a single canonical entry.
    """

    # ----------------------------------------------
    # Speaker structure (pure analytical logic)
    # ----------------------------------------------
    entry["speaker_structure"] = build_speaker_structure(entry)
    entry["micro_analysis"] = build_micro_analysis(entry)

    enrich_entry(entry)

    return entry


def build_manual_entry(
    *,
    date,
    conference,
    session_label,
    speaker_raw,
    signals_text,
    keywords,
) -> Dict:

    timestamp = datetime.now(timezone.utc).isoformat()

    safe_conference = (conference or "").strip()

    entry = {
        # -------------------------
        # Identity & audit
        # -------------------------
        "entry_id": str(uuid.uuid4()),
        "session_id": safe_conference.replace(" ", "").upper() or None,

        "source_file": "manual_entry",
        "row_number": None,
        "ingested_at": timestamp,

        # -------------------------
        # Context
        # -------------------------
        "date": date.isoformat() if date else None,
        "conference": safe_conference or None,
        "session_label": (session_label or "").strip() or None,

        # -------------------------
        # Speaker (RAW)
        # -------------------------
        "country": (speaker_raw or "").strip() or None,
        "country_group": None,

        # -------------------------
        # Content
        # -------------------------
        "signals_text": (signals_text or "").strip() or None,
        "keywords": keywords or [],
    }

    return ingest_manual_entry(entry)
