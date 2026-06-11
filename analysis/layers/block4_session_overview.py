from collections import defaultdict, Counter
from typing import Dict, Any, List


def normalize(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def analyze_session_overview(
    entries: List[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:

    # ----------------------------------------------
    # 1. BUILD SUBJECT MAP (keyword → subjects)
    # ----------------------------------------------

    keyword_to_subjects = defaultdict(set)
    subject_labels = {}

    for sid, data in cfg.get("keyword_aggregations", {}).items():
        label = data.get("label", sid)
        subject_labels[sid] = label
        for k in data.get("members", []):
            keyword_to_subjects[normalize(k)].add(sid)

    # ----------------------------------------------
    # 2. COLLECT SUBJECT DATA
    # ----------------------------------------------

    subjects = defaultdict(lambda: {
        "entries": 0,
        "countries": Counter(),
        "angles": Counter(),
        "posture": Counter(),
        "explicitness": Counter(),
        "risk": Counter(),
        "entry_ids": set(),          # ✅ INITIALISÉ ICI
    })

    for e in entries:
        keywords = [normalize(k) for k in e.get("keywords", [])]

        country = (
            e.get("speaker_structure", {})
             .get("primary_speaker", {})
             .get("name")
        )

        micro = e.get("micro_analysis", {})
        entry_id = e.get("entry_id")     # ✅ DÉFINI ICI

        # subjects touched by this entry
        touched_subjects = set()

        for k in keywords:
            if k in keyword_to_subjects:
                touched_subjects.update(keyword_to_subjects[k])
            else:
                touched_subjects.add(k)

        for subj in touched_subjects:
            s = subjects[subj]
            s["entries"] += 1

            if entry_id:
                s["entry_ids"].add(entry_id)   # ✅ UTILISÉ ICI

            if country:
                s["countries"][country] += 1

            # angles = co-occurring keywords
            for other in keywords:
                if other != subj:
                    s["angles"][other] += 1

            # micro-analysis aggregation
            if "diplomatic_posture" in micro:
                s["posture"][micro["diplomatic_posture"]] += 1

            if "explicitness_level" in micro:
                s["explicitness"][micro["explicitness_level"]] += 1

            if "risk_level" in micro:
                s["risk"][micro["risk_level"]] += 1

    # ----------------------------------------------
    # 3. FORMAT OUTPUT
    # ----------------------------------------------

    out = []

    for subj, data in subjects.items():
        label = subject_labels.get(subj, subj)

        out.append({
            "subject": label,
            "entries": data["entries"],
            "countries_total": len(data["countries"]),
            "top_countries": [
                c for c, _ in data["countries"].most_common(
                    cfg["limits"]["top_countries"]
                )
            ],
            "angles": [
                k for k, _ in data["angles"].most_common(
                    cfg["limits"]["top_angles"]
                )
            ],
            "posture": dict(data["posture"]),
            "explicitness": dict(data["explicitness"]),
            "risk": dict(data["risk"]),
            "entry_ids": sorted(data["entry_ids"]),   # ✅ SORTIE
        })

    return sorted(
        out,
        key=lambda x: x["entries"],
        reverse=True
    )[: cfg["limits"]["top_subjects"]]
