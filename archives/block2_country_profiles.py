import json
from pathlib import Path
from collections import defaultdict, Counter

# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
FEATURES_DIR = BASE_DIR / "features"
PROFILES_DIR = BASE_DIR / "profiles"

PROFILES_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# Constants (FIGÉES)
# --------------------------------------------------

POSTURES = ["procedural", "passive", "cooperative", "assertive"]
GESTURES = ["statement", "appeal", "positioning", "reaffirmation", "announcement"]
EXPLICITNESS = ["low", "medium", "high"]

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def most_common(values):
    if not values:
        return "unknown"
    return Counter(values).most_common(1)[0][0]

def classify_volatility(counts, total):
    if total <= 1:
        return "low"
    dominant = max(counts.values())
    ratio = dominant / total
    if ratio >= 0.7:
        return "low"
    if ratio >= 0.45:
        return "medium"
    return "high"

def classify_diversity(n):
    if n <= 1:
        return "low"
    if n <= 3:
        return "medium"
    return "high"

def classify_risk_tolerance(high_risk, total):
    if total == 0:
        return "low"
    r = high_risk / total
    if r >= 0.25:
        return "high"
    if r >= 0.10:
        return "medium"
    return "low"

def empty_counter(keys):
    return {k: 0 for k in keys}

# --------------------------------------------------
# Main
# --------------------------------------------------

def process(session_id: str):
    infile = FEATURES_DIR / f"{session_id}_entries_micro_v1_2.jsonl"
    outfile = PROFILES_DIR / f"{session_id}_country_profiles_v1.json"

    by_country = defaultdict(list)

    with open(infile, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)

            speaker = e.get("speaker_structure", {}).get("primary_speaker", {})
            country = speaker.get("name")

            # 🔒 RULE: one profile = one country only
            if not country or country == "unknown":
                continue

            by_country[country].append(e)

    profiles = []

    for country, entries in by_country.items():
        total = len(entries)

        regional_groups = []
        solo = coalition = 0

        posture_counts = empty_counter(POSTURES)
        gesture_counts = empty_counter(GESTURES)
        explicitness_counts = empty_counter(EXPLICITNESS)

        central_topics = Counter()
        secondary_topics = Counter()

        high_risk = novelty = 0
        acts = Counter()
        alignments = Counter()

        for e in entries:
            speaker = e["speaker_structure"]["primary_speaker"]
            micro = e["micro_analysis"]

            regional_groups.append(speaker.get("regional_group", "unknown"))

            if e["speaker_structure"].get("coalition", {}).get("is_coalition"):
                coalition += 1
            else:
                solo += 1

            posture = micro.get("diplomatic_posture")
            if posture in posture_counts:
                posture_counts[posture] += 1

            gesture = micro.get("discursive_gesture")
            if gesture in gesture_counts:
                gesture_counts[gesture] += 1

            exp = micro.get("explicitness_level")
            if exp in explicitness_counts:
                explicitness_counts[exp] += 1

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
            "session_id": session_id,
            "country": country,
            "regional_group": most_common([g for g in regional_groups if g != "unknown"]),

            "activity": {
                "interventions_count": total,
                "solo_interventions": solo,
                "coalition_interventions": coalition
            },

            "posture": {
                "dominant": max(posture_counts, key=posture_counts.get),
                "distribution": posture_counts,
                "volatility": classify_volatility(posture_counts, total)
            },

            "topics": {
                "central": dict(central_topics),
                "secondary": dict(secondary_topics),
                "diversity": classify_diversity(
                    len(set(central_topics) | set(secondary_topics))
                )
            },

            "narrative_style": {
                "discursive_gestures": gesture_counts,
                "explicitness_levels": explicitness_counts
            },

            "risk_profile": {
                "high_risk_interventions": high_risk,
                "novelty_signals": novelty,
                "risk_tolerance": classify_risk_tolerance(high_risk, total)
            },

            "diplomatic_behavior": {
                "announcements": acts.get("announcement", 0),
                "candidacies": acts.get("candidacy", 0),
                "initiative_launches": acts.get("initiative_launch", 0),
                "invitations": acts.get("invitation", 0),
                "report_references": acts.get("report_reference", 0),
                "procedural_openings": acts.get("procedural_opening", 0)
            },

            "political_alignments": {
                "invoked": dict(alignments)
            }
        }

        profiles.append(profile)

    profiles.sort(key=lambda p: p["country"].lower())

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    print(f"[OK] Block 2 country profiles V1 generated → {outfile}")

# --------------------------------------------------
# CLI
# --------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python block2_country_profiles_v1.py <SESSION_ID>")
    else:
        process(sys.argv[1])
