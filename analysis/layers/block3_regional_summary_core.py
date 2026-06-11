# -*- coding: utf-8 -*-
"""
Block 3 — Regional Summary (CORE)

Responsibilities:
- Aggregate country profiles (Block 2) at regional level
- Identify dominant posture, regional concerns
- Classify countries as leaders / aligned / dissident

PURE analytical core:
- no file I/O
- no CLI
- no Streamlit
"""

from collections import defaultdict, Counter
from typing import List, Dict, Any


# ==================================================
# Helpers
# ==================================================

def posture_distance(p1: str, p2: str, order: List[str]) -> int:
    if not p1 or not p2:
        return 0
    if p1 not in order or p2 not in order:
        return 0
    return abs(order.index(p1) - order.index(p2))


def classify_regional_concerns(
    topic_counts: Dict[str, int],
    member_count: int,
    ratio: float
) -> List[str]:
    """
    A topic is considered a regional concern if it is
    raised by at least (ratio * member_count) countries.
    """
    threshold = max(1, int(member_count * ratio))
    return sorted(
        [t for t, v in topic_counts.items() if v >= threshold]
    )


# ==================================================
# CORE
# ==================================================

def analyze_regional_summary(
    profiles: List[Dict[str, Any]],
    cfg
) -> List[Dict[str, Any]]:
    """
    Args:
        profiles: output of Block 2 (country profiles)
        cfg: full config object (expects cfg.block3)

    Returns:
        List of regional summaries, sorted by region name
    """

    block3 = cfg.block3
    thr = block3.get("thresholds", {})
    rules = block3.get("rules", {})

    posture_order = block3.get(
        "posture_order",
        ["procedural", "passive", "cooperative", "assertive"]
    )

    by_region = defaultdict(list)

    # --------------------------------------------------
    # Group profiles by region
    # --------------------------------------------------

    for p in profiles:
        region = (p.get("regional_group") or "").strip()

        if not region and rules.get("ignore_missing_region", True):
            continue

        by_region[region].append(p)

    summaries = []

    # --------------------------------------------------
    # Analyze each region
    # --------------------------------------------------

    for region, members in by_region.items():
        posture_counts = Counter()
        topic_counts = Counter()
        activity = []

        for p in members:
            country = p["country"]

            posture_counts[p["posture"]["dominant"]] += 1

            for t in p.get("topics", {}).get("central", {}).keys():
                topic_counts[t] += 1

            activity.append(
                (country, p["activity"]["interventions_count"])
            )

        # Dominant posture
        dominant_posture = posture_counts.most_common(1)[0][0]

        # Regional concerns
        regional_concerns = classify_regional_concerns(
            topic_counts,
            len(members),
            thr.get("regional_concern_ratio", 0.3)
        )

        # Identify leaders by activity
        activity.sort(key=lambda x: x[1], reverse=True)
        leaders = [
            c for c, _ in activity[: thr.get("leaders_count", 3)]
        ]

        aligned = []
        dissident = []

        # --------------------------------------------------
        # Classify countries
        # --------------------------------------------------

        for p in members:
            country = p["country"]

            if country in leaders:
                continue

            interventions = p["activity"]["interventions_count"]
            is_active = interventions >= thr.get("min_activity", 2)

            dist = posture_distance(
                p["posture"]["dominant"],
                dominant_posture,
                posture_order
            )

            country_topics = set(p.get("topics", {}).get("central", {}).keys())
            non_regional_topics = [
                t for t in country_topics if t not in regional_concerns
            ]

            # Posture dissidence
            if dist >= thr.get("posture_deviation_distance", 2):
                dissident.append({
                    "country": country,
                    "deviation": {
                        "type": "posture",
                        "detail": "posture deviates from regional norm"
                    }
                })

            # Topic dissidence
            elif is_active and non_regional_topics:
                dissident.append({
                    "country": country,
                    "deviation": {
                        "type": "topic",
                        "detail": (
                            "emphasizes non-regional topic(s): "
                            + ", ".join(sorted(non_regional_topics))
                        )
                    }
                })

            else:
                aligned.append(country)

        summaries.append({
            "region": region,
            "dominant_posture": dominant_posture,
            "regional_concerns": regional_concerns,
            "countries": {
                "leaders": leaders,
                "aligned": sorted(aligned),
                "dissident": dissident
            }
        })

    return sorted(summaries, key=lambda x: x["region"].lower())
