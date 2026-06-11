# -*- coding: utf-8 -*-
"""
Block 2 — Country Profiles (Core)

PURE analytical core:
- no file I/O
- no CLI
- no Streamlit
"""

from collections import defaultdict, Counter
from typing import List, Dict, Any


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def most_common(values):
    if not values:
        return "unknown"
    return Counter(values).most_common(1)[0][0]


def classify_volatility(counts: Dict[str, int], total: int, cfg) -> str:
    if total <= 1:
        return "low"

    dominant = max(counts.values())
    ratio = dominant / total

    if ratio >= cfg["low"]:
        return "low"
    if ratio >= cfg["medium"]:
        return "medium"
    return "high"


def classify_diversity(n: int, cfg) -> str:
    if n <= cfg["low"]:
        return "low"
    if n <= cfg["medium"]:
        return "medium"
    return "high"


def classify_risk_tolerance(high_risk: int, total: int, cfg) -> str:
    if total == 0:
        return "low"

    r = high_risk / total

    if r >= cfg["high"]:
        return "high"
    if r >= cfg["medium"]:
        return "medium"
    return "low"


def empty_counter(keys):
    return {k: 0 for k in keys}


# --------------------------------------------------
# CORE
# --------------------------------------------------

def analyze_country_profiles(
    entries: List[Dict[str, Any]],
    cfg
) -> List[Dict[str, Any]]:

    block2 = cfg.block2
    tax = block2["taxonomies"]
    thr = block2["thresholds"]

    POSTURES = tax["diplomatic_postures"]
    GESTURES = tax["discursive_gestures"]
    EXPLICITNESS = tax["explicitness_levels"]

    by_country = defaultdict(list)

    for e in entries:
        speaker = e.get("speaker_structure", {}).get("primary_speaker", {})
        country = speaker.get("name")

        if not country or country in block2["rules"]["ignore_speakers"]:
            continue

        by_country[country].append(e)

    profiles = []

    for country, country_entries in by_country.items():
        total = len(country_entries)

        posture_counts = empty_counter(POSTURES)
        gesture_counts = empty_counter(GESTURES)
        explicitness_counts = empty_counter(EXPLICITNESS)

        regional_groups = []
        solo = coalition = 0

        central_topics = Counter()
        secondary_topics = Counter()

        high_risk = novelty = 0
        acts = Counter()
        alignments = Counter()

        for e in country_entries:
            speaker = e["speaker_structure"]["primary_speaker"]
            micro = e["micro_analysis"]

            regional_groups.append(speaker.get("regional_group", "unknown"))

            if e["speaker_structure"].get("coalition", {}).get("is_coalition"):
                coalition += 1
            else:
                solo += 1

            if micro.get("diplomatic_posture") in posture_counts:
                posture_counts[micro["diplomatic_posture"]] += 1

            if micro.get("discursive_gesture") in gesture_counts:
                gesture_counts[micro["discursive_gesture"]] += 1

            if micro.get("explicitness_level") in explicitness_counts:
                explicitness_counts[micro["explicitness_level"]] += 1

            for t in micro.get("topics_analysis", {}).get("central_topics", []):
                central_topics[t] += 1

            for t in micro.get("topics_analysis", {}).get("secondary_topics", []):
                secondary_topics[t] += 1

            if micro.get("risk_level") == "high":
                high_risk += 1

            if micro.get("novelty_signal"):
                novelty += 1

            for k, v in micro.get("diplomatic_acts", {}).items():
                if v:
                    acts[k] += 1

            for g in e["speaker_structure"].get("alignment_groups", []):
                alignments[g] += 1

        profile = {
            "country": country,
            "regional_group": most_common(
                [g for g in regional_groups if g != "unknown"]
            ),

            "activity": {
                "interventions_count": total,
                "solo_interventions": solo,
                "coalition_interventions": coalition,
            },

            "posture": {
                "dominant": max(posture_counts, key=posture_counts.get),
                "distribution": posture_counts,
                "volatility": classify_volatility(
                    posture_counts, total, thr["volatility"]
                ),
            },

            "topics": {
                "central": dict(central_topics),
                "secondary": dict(secondary_topics),
                "diversity": classify_diversity(
                    len(set(central_topics) | set(secondary_topics)),
                    thr["diversity"],
                ),
            },

            "narrative_style": {
                "discursive_gestures": gesture_counts,
                "explicitness_levels": explicitness_counts,
            },

            "risk_profile": {
                "high_risk_interventions": high_risk,
                "novelty_signals": novelty,
                "risk_tolerance": classify_risk_tolerance(
                    high_risk, total, thr["risk_tolerance"]
                ),
            },

            "diplomatic_behavior": dict(acts),
            "political_alignments": dict(alignments),
        }

        profiles.append(profile)

    return sorted(profiles, key=lambda p: p["country"].lower())
