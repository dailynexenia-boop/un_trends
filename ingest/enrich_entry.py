from typing import Dict

from analysis.speaker_structure import COUNTRY_TO_REGIONAL


def enrich_entry(entry: Dict) -> Dict:
    """
    Enrich a canonical entry in-place with
    deterministic, structural fields.

    This function must be called ONCE at ingest time.
    """

    ss = entry.get("speaker_structure", {})
    primary = ss.get("primary_speaker", {})

    # --------------------------------------------------
    # PRIMARY SPEAKER
    # --------------------------------------------------
    primary_name = primary.get("name")

    entry["primary_speaker"] = primary_name

    entry["primary_speaker_type"] = (
        "state" if primary.get("is_state")
        else "institution" if primary.get("is_institution")
        else "individual" if primary.get("is_individual")
        else "unknown"
    )

    # --------------------------------------------------
    # REGIONAL GROUP (DETERMINISTIC)
    # --------------------------------------------------
    regional = primary.get("regional_group")

    if not regional or regional == "unknown":
        # fallback: infer from country registry
        regional = COUNTRY_TO_REGIONAL.get(primary_name, "unknown")

    entry["regional_group"] = regional

    # --------------------------------------------------
    # ALIGNMENT GROUPS
    # --------------------------------------------------
    entry["alignment_groups"] = ss.get("alignment_groups", [])

    # --------------------------------------------------
    # COALITION / SECONDARY SPEAKERS
    # --------------------------------------------------
    coalition = ss.get("coalition", {})

    entry["secondary_speakers"] = coalition.get(
        "countries_mentioned", []
    )

    entry["is_coalition"] = coalition.get(
        "is_coalition", False
    )

    return entry
