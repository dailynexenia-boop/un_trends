# -*- coding: utf-8 -*-
"""
Block 5 — Session Overview (Canonical, Live View)

- Canonical-driven
- Rules loaded from config/block4.yaml (block5 section)
- NO file output (live view only)
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List

import yaml


# ==================================================
# PATHS
# ==================================================

CANONICAL_REL = Path("canonical/canonical.jsonl")
CONFIG_REL = Path("config/block4.yaml")


# ==================================================
# LOADERS
# ==================================================

def load_block5_config(project_root: Path) -> dict:
    cfg_path = project_root / CONFIG_REL
    if not cfg_path.exists():
        raise FileNotFoundError("config/block4.yaml not found")

    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    if "block5" not in cfg:
        raise KeyError("block5 section missing in block4.yaml")

    return cfg["block5"]


def load_canonical(project_root: Path) -> List[Dict[str, Any]]:
    path = project_root / CANONICAL_REL
    if not path.exists():
        return []

    entries: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    return entries


# ==================================================
# CORE ANALYSIS
# ==================================================

def analyze_session_overview(
    session_key: str,
    project_root: Path,
) -> Dict[str, Any]:

    cfg = load_block5_config(project_root)
    entries = load_canonical(project_root)

    # ------------------------------
    # SESSION MATCHING
    # ------------------------------

    match_on = cfg["matching"]["match_on"]
    normalize = cfg["matching"].get("normalize", False)

    def norm(val: Any) -> str:
        s = str(val or "")
        return s.replace(" ", "").lower() if normalize else s

    session_entries = [
        e for e in entries
        if norm(e.get(match_on)) == norm(session_key)
    ]

    if not session_entries:
        return {
            "session_id": session_key,
            "error": "No canonical entries matched",
            "meta": {
                "schema_version": cfg["ui"]["schema_version"],
                "entries_scanned": len(entries),
                "entries_matched": 0,
            },
        }

    # ------------------------------
    # SIGNAL COLLECTION
    # ------------------------------

    actors = Counter()
    alignment_groups = Counter()
    regional_groups = Counter()

    risk_levels = Counter()
    watch_count = 0

    diplomatic_postures = Counter()
    explicitness_levels = Counter()

    central_topics = Counter()
    secondary_topics = Counter()

    state_count = 0
    topic_weights = cfg["topic_weights"]

    for e in session_entries:
        micro = e.get("micro_analysis") or {}
        speaker = e.get("speaker_structure") or {}
        primary = speaker.get("primary_speaker") or {}

        # Actors
        actor = primary.get("name") or speaker.get("speaker_raw")
        if actor:
            actors[actor] += 1

        for g in speaker.get("alignment_groups") or []:
            alignment_groups[g] += 1

        rg = primary.get("regional_group")
        if rg:
            regional_groups[rg] += 1

        if primary.get("is_state"):
            state_count += 1

        # Risk & posture
        rl = micro.get("risk_level")
        if rl:
            risk_levels[rl] += 1

        if micro.get("watch_flag"):
            watch_count += 1

        dp = micro.get("diplomatic_posture")
        if dp:
            diplomatic_postures[dp] += 1

        ex = micro.get("explicitness_level")
        if ex:
            explicitness_levels[ex] += 1

        # Topics
        topics = micro.get("topics_analysis") or {}
        for t in topics.get("central_topics") or []:
            central_topics[t] += topic_weights["central"]
        for t in topics.get("secondary_topics") or []:
            secondary_topics[t] += topic_weights["secondary"]

    total_entries = len(session_entries)

    # ------------------------------
    # DERIVED METRICS (YAML RULES)
    # ------------------------------

    dominant_perception: List[str] = []
    if diplomatic_postures:
        dominant_perception.append(diplomatic_postures.most_common(1)[0][0])
    if explicitness_levels:
        dominant_perception.append(explicitness_levels.most_common(1)[0][0])

    # Fragmentation
    frag_cfg = cfg["fragmentation"]
    fragmentation = "low"
    if (
        len(actors) >= frag_cfg["medium"]["min_actors"]
        or len(alignment_groups) >= frag_cfg["medium"]["min_alignment_groups"]
    ):
        fragmentation = "medium"
    if (
        len(actors) >= frag_cfg["high"]["min_actors"]
        or len(alignment_groups) >= frag_cfg["high"]["min_alignment_groups"]
    ):
        fragmentation = "high"

    # Institutional density
    inst_cfg = cfg["institutional_density"]
    ratio = state_count / max(1, total_entries)
    institutional_density = "low"
    if ratio >= inst_cfg["medium_threshold"]:
        institutional_density = "medium"
    if ratio >= inst_cfg["high_threshold"]:
        institutional_density = "high"

    # Spillover risk
    spill_cfg = cfg["spillover_risk"]
    spillover = "low"
    if risk_levels.get("high", 0) >= spill_cfg["medium_min_high_risk"]:
        spillover = "medium"
    if risk_levels.get("high", 0) >= spill_cfg["high_min_high_risk"]:
        spillover = "high"

    # Bridge potential
    bridge_cfg = cfg["bridge_potential"]
    bridge = "medium"
    if (
        fragmentation == bridge_cfg["low_if"]["fragmentation"]
        and institutional_density == bridge_cfg["low_if"]["institutional_density"]
    ):
        bridge = "low"
    if (
        fragmentation == bridge_cfg["high_if"]["fragmentation"]
        and institutional_density == bridge_cfg["high_if"]["institutional_density"]
    ):
        bridge = "high"

    # Agenda drivers
    agenda_drivers = [
        t for t, _ in central_topics.most_common(
            cfg["agenda_drivers"]["max_items"]
        )
    ]

    # ------------------------------
    # OUTPUT (LIVE VIEW)
    # ------------------------------

    return {
        "session_id": session_key,
        "session_overview": {
            "total_entries": total_entries,
            "dominant_perception": dominant_perception,
            "fragmentation_level": fragmentation,
            "institutional_density": institutional_density,
        },
        "subject_landscape": {
            "core": [{"topic": t, "weight": w} for t, w in central_topics.most_common(5)],
            "secondary": [{"topic": t, "weight": w} for t, w in secondary_topics.most_common(10)],
        },
        "actor_configuration": {
            "top_actors": actors.most_common(10),
            "alignment_groups": alignment_groups.most_common(),
            "regional_groups": regional_groups.most_common(),
        },
        "strategic_reading": {
            "agenda_drivers": agenda_drivers,
            "spillover_risk": spillover,
            "bridge_potential": bridge,
            "watch_pressure": watch_count,
        },
        "meta": {
            "schema_version": cfg["ui"]["schema_version"],
            "entries_scanned": len(entries),
            "entries_matched": total_entries,
        },
    }
