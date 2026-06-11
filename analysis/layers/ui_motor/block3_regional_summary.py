# -*- coding: utf-8 -*-
"""
Block 3 — Regional Summary (Core)

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

def posture_distance(p1: str, p2: str, order: List[str]) -> int:
    if p1 not in order or p2 not in order:
        return 0
    return abs(order.index(p1) - order.index(p2))


def classify_regional_concerns(
    topic_counts: Dict[str, int],
    member_count: int,
    ratio: float
) -> List[str]:
    threshold = max(1, int(member_count * ratio))
    return sorted(
        [t for t, v in topic_counts.items() if v >= threshold]
    )


# --------------------------------------------------
# CORE
# --------------------------------------------------

def analyze_regional_summary(
    profiles: List[Dict[str, Any]],
    cfg
) -> List[Dict[str, Any]]:

    block3 = cfg.block3
    tax = block3["taxonomies"]
    thr = block3["thresholds"]
    rules = block3["rules"]

    POSTURES = tax["diplomatic_postures"]

    by_region = defaultdict(list)

    for p in profiles:
        region = (p.get("regional_group") or "").strip()
        if not region and rules["ignore_missing_region"]:
            continue
        by_region[region].append(p)

    summaries = []

    for region, members in by_region.items():

        posture_counts = Counter()
        topic_counts = Counter()
        activity = []

        for p in members:
            posture_counts[p["posture"]["dominant"]] += 1

            for t in p["topics"]["central"].keys():
                topic_counts[t] += 1

            activity.append(
                (p["country"], p["activity"]["interventions_count"])
            )

        dominant_posture = posture_counts.most_common(1)[0][0]

        regional_concerns = classify_regional_concerns(
            topic_counts,
            len(members),
            thr["regional_concern_ratio"]
        )

        activity.sort(key=lambda x: x[1], reverse=True)
        leaders = [
            c for c, _ in activity[:thr["leaders_count"]]
        ]

        aligned = []
        dissident = []

        for p in members:
            country = p["country"]

            if country in leaders:
                continue

            interventions = p["activity"]["interventions_count"]
            is_active = interventions >= thr["min_activity"]

            dist = posture_distance(
                p["posture"]["dominant"],
                dominant_posture,
                POSTURES
            )

            country_topics = set(p["topics"]["central"].keys())
            non_regional_topics = [
                t for t in country_topics if t not in regional_concerns
            ]

            if dist >= thr["posture_deviation_distance"]:
                dissident.append({
                    "country": country,
                    "deviation": {
                        "type": "posture",
                        "detail": "posture deviates from regional norm"
                    }
                })

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
            "regional_concerns": regional_concerns,
            "countries": {
                "leaders": leaders,
                "aligned": sorted(aligned),
                "dissident": dissident
            }
        })

    return sorted(summaries, key=lambda x: x["region"].lower())
