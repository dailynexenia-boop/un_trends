import json
import yaml
from pathlib import Path
from typing import Dict

# ==================================================
# PROJECT ROOT (robuste pour script + module)
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"

COUNTRIES_YAML = CONFIG_DIR / "countries.yaml"
ALIGNMENT_GROUPS_YAML = CONFIG_DIR / "alignment_groups.yaml"
INSTITUTIONS_YAML = CONFIG_DIR / "institutions.yaml"

# ==================================================
# LOAD YAML
# ==================================================

def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

COUNTRIES_CFG = load_yaml(COUNTRIES_YAML)
ALIGNMENT_GROUPS = set(load_yaml(ALIGNMENT_GROUPS_YAML))
INSTITUTIONS = set(load_yaml(INSTITUTIONS_YAML))

# ==================================================
# LOOKUP TABLES
# ==================================================

COUNTRY_ALIAS_TO_CANON = {}
COUNTRY_TO_REGIONAL = {}

for canon, meta in COUNTRIES_CFG.items():
    COUNTRY_TO_REGIONAL[canon] = meta.get("regional_group", "unknown")
    for alias in meta.get("aliases", []):
        COUNTRY_ALIAS_TO_CANON[alias] = canon

# ==================================================
# HELPERS
# ==================================================

def normalize_country(name: str) -> str | None:
    if not name:
        return None
    return COUNTRY_ALIAS_TO_CANON.get(name.strip(), name.strip())


def is_state(name: str) -> bool:
    return name in COUNTRY_TO_REGIONAL


def looks_like_person_name(name: str) -> bool:
    if not name:
        return False
    parts = name.split()
    return (
        len(parts) == 2
        and all(p[:1].isupper() for p in parts)
        and name.upper() != name
    )

# ==================================================
# CORE FUNCTION (PARTAGÉE)
# ==================================================

def build_speaker_structure(entry: Dict) -> Dict:
    """
    Build speaker structure from a canonical entry dict.
    Shared by:
    - CSV batch build
    - manual editor ingestion
    """

    raw = (entry.get("country") or "").strip()
    tokens_raw = [t.strip() for t in raw.split(",") if t.strip()]
    tokens = [normalize_country(t) for t in tokens_raw]

    # -------------------------
    # FIND PRIMARY SPEAKER
    # -------------------------

    primary = None

    for t in tokens:
        if is_state(t):
            primary = t
            break

    if not primary and "EU" in tokens:
        primary = "EU"

    if not primary:
        primary = "unknown"

    # -------------------------
    # PRIMARY SPEAKER STRUCT
    # -------------------------

    primary_is_state = is_state(primary)
    primary_is_eu = primary == "EU"

    regional_group = (
        COUNTRY_TO_REGIONAL.get(primary, "unknown")
        if primary_is_state
        else "unknown"
    )

    primary_speaker = {
        "name": primary,
        "is_state": primary_is_state,
        "is_alignment_group": False,
        "is_institution": primary in INSTITUTIONS,
        "is_individual": (
            not primary_is_state
            and not primary_is_eu
            and looks_like_person_name(primary)
        ),
        "regional_group": regional_group,
    }

    # -------------------------
    # ALIGNMENT GROUPS
    # -------------------------

    alignment_groups = sorted({
        t for t in tokens
        if t in ALIGNMENT_GROUPS and t != primary
    })

    # -------------------------
    # COALITION COUNTRIES
    # -------------------------

    coalition_countries = sorted({
        t for t in tokens
        if is_state(t) and t != primary
    })

    return {
        "speaker_raw": raw,
        "primary_speaker": primary_speaker,
        "alignment_groups": alignment_groups,
        "coalition": {
            "is_coalition": len(coalition_countries) > 0,
            "countries_mentioned": coalition_countries,
        },
    }

# ==================================================
# CLI (LEGACY, OPTIONNEL)
# ==================================================

def process(infile: Path, outfile: Path):
    with open(infile, encoding="utf-8") as fin, \
         open(outfile, "w", encoding="utf-8") as fout:

        for line in fin:
            entry = json.loads(line)
            entry["speaker_structure"] = build_speaker_structure(entry)
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[OK] Speaker structure generated → {outfile}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python speaker_structure.py <input_jsonl> <output_jsonl>")
        sys.exit(1)

    process(Path(sys.argv[1]), Path(sys.argv[2]))
