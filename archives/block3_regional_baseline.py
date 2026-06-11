import json
from pathlib import Path
from collections import defaultdict, Counter

# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROFILES_DIR = BASE_DIR / "profiles"
OUTPUT_DIR = BASE_DIR / "regional"

OUTPUT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# Constants
# --------------------------------------------------

POSTURE_ORDER = ["procedural", "passive", "cooperative", "assertive"]

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def posture_distance(p1, p2):
    if p1 not in POSTURE_ORDER or p2 not in POSTURE_ORDER:
        return 0
    return abs(POSTURE_ORDER.index(p1) - POSTURE_ORDER.index(p2))


def classify_regional_concerns(topic_counts, member_count):
    """
    A topic is a regional concern if it is emphasized
    by at least 25% of regional members.
    """
    threshold = max(1, int(member_count * 0.25))
    return sorted([t for t, v in topic_counts.items() if v >= threshold])


# --------------------------------------------------
# Main
# --------------------------------------------------

def process(session_id: str):

    profiles_path = PROFILES_DIR / f"{session_id}_country_profiles_v1.json"
    if not profiles_path.exists():
        raise FileNotFoundError(profiles_path)

    with open(profiles_path, encoding="utf-8") as f:
        profiles = json.load(f)

    # --------------------------------------------------
    # Group countries STRICTLY by UN regional group
    # --------------------------------------------------

    by_region = defaultdict(list)
    for p in profiles:
        region = (p.get("regional_group") or "").strip()
        if region:
            by_region[region].append(p)

    summaries = []

    # --------------------------------------------------
    # Process each region
    # --------------------------------------------------

    for region, members in by_region.items():

        # -------------------------
        # Build simple regional baseline
        # -------------------------

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
            topic_counts, len(members)
        )

        # Leaders = top 3 by activity
        activity.sort(key=lambda x: x[1], reverse=True)
        leaders = [c for c, _ in activity[:3]]

        aligned = []
        dissident = []

        # -------------------------
        # Position countries
        # -------------------------

        for p in members:
            country = p["country"]

            if country in leaders:
                continue

            country_posture = p["posture"]["dominant"]
            dist = posture_distance(country_posture, dominant_posture)

            country_topics = set(p["topics"]["central"].keys())
            non_regional_topics = [
                t for t in country_topics if t not in regional_concerns
            ]

            interventions = p["activity"]["interventions_count"]
            is_active = interventions >= 2  # minimal activity threshold

            # ---- Dissidence logic (STRICT) ----

            if dist >= 2:
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
            "session_id": session_id,
            "region": region,
            "regional_concerns": regional_concerns,
            "countries": {
                "leaders": leaders,
                "aligned": sorted(aligned),
                "dissident": dissident
            }
        })

    summaries.sort(key=lambda x: x["region"].lower())

    out = OUTPUT_DIR / f"{session_id}_regional_summary_v1.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

    print(f"[OK] Block 3 regional summary generated → {out}")


# --------------------------------------------------
# CLI
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python block3_regional_summary.py <SESSION_ID>")
    else:
        process(sys.argv[1])
