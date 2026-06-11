from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from datetime import datetime, timedelta
from typing import Dict, Any

from analysis.speaker_structure import build_speaker_structure
from analysis.micro_analysis import build_micro_analysis, load_topic_registers
from analysis.micro_config_loader import load_micro_analysis_config

# ==================================================
# PATHS
# ==================================================

CANONICAL_PATH = (
    Path(__file__).resolve().parents[1]
    / "canonical"
    / "canonical.jsonl"
)


# ==================================================
# ANALYSIS STATUS HELPERS
# ==================================================

def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def should_recompute_pending(
    entry: Dict[str, Any],
    max_age_hours: int | None = None,
) -> bool:
    """
    Decide whether an entry should be recomputed.
    Used for PARTIAL recompute (editor workflow).
    """

    status = entry.get("analysis_status")

    # No status → legacy entry → recompute
    if not status:
        return True

    if not status.get("micro_analysis_applied"):
        return True

    if max_age_hours is not None:
        last = status.get("last_computed_at")
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                return datetime.utcnow() - last_dt > timedelta(hours=max_age_hours)
            except Exception:
                return True

    return False


def mark_computed(entry: Dict[str, Any]) -> None:
    entry["analysis_status"] = {
        "speaker_structure_applied": True,
        "micro_analysis_applied": True,
        "last_computed_at": _now_iso(),
    }


# ==================================================
# CORE RECOMPUTE LOGIC
# ==================================================

def _recompute_entry(
    entry: Dict[str, Any],
    micro_cfg: Dict[str, Any],
    topic_registers: Dict[str, Any],
) -> None:
    entry["speaker_structure"] = build_speaker_structure(entry)
    entry["micro_analysis"] = build_micro_analysis(entry, micro_cfg, topic_registers)
    mark_computed(entry)


# ==================================================
# PUBLIC MODES
# ==================================================

def recompute_pending_only(
    max_age_hours: int | None = 24,
) -> int:
    """
    Recompute ONLY entries that:
    - are new / pending
    - or older than max_age_hours (if provided)

    Returns number of recomputed entries.
    """

    if not CANONICAL_PATH.exists():
        raise FileNotFoundError("canonical.jsonl not found")

    micro_cfg = load_micro_analysis_config(strict=False)
    topic_registers = load_topic_registers()

    tmp_path = CANONICAL_PATH.with_suffix(".tmp")
    updated = 0

    with open(CANONICAL_PATH, encoding="utf-8") as fin, \
         open(tmp_path, "w", encoding="utf-8") as fout:

        for line in fin:
            entry = json.loads(line)

            if should_recompute_pending(entry, max_age_hours):
                _recompute_entry(entry, micro_cfg, topic_registers)
                updated += 1

            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")

    tmp_path.replace(CANONICAL_PATH)
    return updated


def recompute_all() -> int:
    """
    Recompute ALL entries, regardless of status.
    Used after YAML / doctrine changes.
    """

    if not CANONICAL_PATH.exists():
        raise FileNotFoundError("canonical.jsonl not found")

    micro_cfg = load_micro_analysis_config(strict=False)
    topic_registers = load_topic_registers()

    tmp_path = CANONICAL_PATH.with_suffix(".tmp")
    updated = 0

    with open(CANONICAL_PATH, encoding="utf-8") as fin, \
         open(tmp_path, "w", encoding="utf-8") as fout:

        for line in fin:
            entry = json.loads(line)

            _recompute_entry(entry, micro_cfg, topic_registers)
            updated += 1

            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")

    tmp_path.replace(CANONICAL_PATH)
    return updated


# ==================================================
# CLI
# ==================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        # default: safe editor workflow
        n = recompute_pending_only()
        print(f"[OK] Recomputed {n} pending entries")

    elif sys.argv[1] == "--all":
        n = recompute_all()
        print(f"[OK] Recomputed ALL entries ({n})")

    else:
        print("Usage:")
        print("  python recompute_canonical.py        # pending only")
        print("  python recompute_canonical.py --all  # full recompute")
