# -*- coding: utf-8 -*-
"""
Block 4.1 — Strategic Core (FINAL)

PURE ANALYTICAL CORE

Responsibilities:
- Consume enriched canonical entries
- Apply register detection, political cost logic
- Compute perception dynamics, actor poles
- Produce strategic entry points & missions

NO I/O
NO PATHS
NO SESSION
NO SUBJECT CARDS
"""

import re
from collections import defaultdict, Counter
from typing import List, Dict, Any, Optional


# ==================================================
# TEXT NORMALIZATION
# ==================================================

def normalize(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


# ==================================================
# REGISTER & COST DETECTION (YAML-DRIVEN)
# ==================================================

def detect_registers(text: str, registers_cfg: Dict[str, List[str]]) -> set:
    t = normalize(text)
    found = set()

    for reg, tokens in registers_cfg.items():
        for tok in tokens:
            if tok in t:
                found.add(reg)
                break

    return found


def _regex_match_any(text: str, patterns: List[str]) -> bool:
    for p in patterns or []:
        try:
            if re.search(p, text):
                return True
        except re.error:
            if p in text:
                return True
    return False


def is_high_cost(text: str, cfg: Dict[str, Any]) -> bool:
    return _regex_match_any(text, cfg.get("high", []))


def is_medium_cost(text: str, cfg: Dict[str, Any]) -> bool:
    return _regex_match_any(text, cfg.get("medium", []))


def is_low_cost_candidate(text: str, cfg: Dict[str, Any]) -> bool:
    anchors = cfg.get("low", [])
    t = normalize(text)
    return any(a in t for a in anchors)


# ==================================================
# PERCEPTION DYNAMICS
# ==================================================

def compute_perception(
    entries: List[dict],
    thresholds: Dict[str, Any],
) -> List[str]:

    perception = []
    countries = {e.get("country") for e in entries if e.get("country")}

    inst = thresholds.get("institutionalised", {})
    if (
        len(entries) >= inst.get("min_entries", 20)
        and len(countries) >= inst.get("min_countries", 15)
    ):
        perception.append("institutionalised")

    if any(e.get("_high_cost") for e in entries):
        perception.append("conflictualised")

    return perception


# ==================================================
# ACTOR POLES
# ==================================================

def compute_actor_poles(entries: List[dict]) -> Dict[str, List[str]]:
    """
    Priority:
    accusatory > defensive > normative > exploratory
    """

    poles = defaultdict(set)

    for e in entries:
        country = e.get("country")
        if not country:
            continue

        regs = e.get("_registers", set())
        txt = e.get("_text", "")

        if e.get("_high_cost") or "accusatory_conflictual" in regs:
            poles["accusatory"].add(country)
        elif "defensive_justificatory" in regs:
            poles["defensive"].add(country)
        elif "governance_procedural" in regs:
            poles["exploratory"].add(country)
        else:
            poles["normative"].add(country)

    # priority clean-up
    priority = ["accusatory", "defensive", "normative", "exploratory"]
    assigned = {}

    for p in priority:
        for c in poles.get(p, set()):
            if c not in assigned:
                assigned[c] = p

    final = defaultdict(list)
    for c, p in assigned.items():
        final[p].append(c)

    return {p: sorted(cs) for p, cs in final.items()}


# ==================================================
# ENTRY POINTS (LOW POLITICAL COST)
# ==================================================

def compute_entry_points(
    entries: List[dict],
    buckets_cfg: Dict[str, List[str]],
    cost_cfg: Dict[str, Any],
    preferred_order: List[str],
) -> List[Dict[str, Any]]:

    scores = Counter()
    support = defaultdict(set)

    for e in entries:
        txt = normalize(e.get("_text", ""))

        if is_high_cost(txt, cost_cfg) or is_medium_cost(txt, cost_cfg):
            continue

        for label, patterns in buckets_cfg.items():
            for p in patterns:
                if normalize(p) in txt:
                    scores[label] += 1
                    support[label].add(p)
                    break

    ordered = sorted(
        scores,
        key=lambda b: (-scores[b], preferred_order.index(b) if b in preferred_order else 999)
    )

    return [
        {
            "label": b,
            "score": scores[b],
            "supporting_terms": sorted(support[b]),
        }
        for b in ordered
        if scores[b] > 0
    ]


# ==================================================
# MISSIONS (BRIDGE LOGIC)
# ==================================================

def bridge_score(
    posture: Optional[str],
    topic_count: int,
    weights: Dict[str, int] | None = None,
    topic_bonus: int = 1,
) -> int:
    w = weights or {"normative": 2, "exploratory": 2, "defensive": 1, "accusatory": -2}
    score = w.get(posture, 0)
    if topic_count >= 3:
        score += topic_bonus
    return score


def build_missions_to_contact(
    actor_poles: Dict[str, List[str]],
    country_stats: Dict[str, Dict[str, Any]],
    posture_weights: Dict[str, int] | None = None,
    topic_count_bonus: int = 1,
    max_missions: int = 8,
) -> List[str]:

    accusatory = set(actor_poles.get("accusatory", []))
    candidates = []

    for pole in ("normative", "exploratory", "defensive"):
        for c in actor_poles.get(pole, []):
            if c not in accusatory:
                candidates.append(c)

    ranked = []
    for c in candidates:
        stats = country_stats.get(c, {})
        ranked.append(
            (c, bridge_score(stats.get("posture"), stats.get("topic_count", 0), posture_weights, topic_count_bonus))
        )

    ranked.sort(key=lambda x: x[1], reverse=True)

    return [c for c, _ in ranked[:max_missions]]


# ==================================================
# MAIN CORE ENTRYPOINT
# ==================================================

def analyze_strategic_subject(
    entries: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    *,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    entries MUST already contain:
    - country
    - signals_text
    - keywords

    This function enriches entries internally.
    """

    registers_cfg = cfg["registers"]
    cost_cfg = cfg["political_cost"]

    enriched = []

    for e in entries:
        text = f"{e.get('signals_text', '')} " + " ".join(e.get("keywords", []))
        regs = detect_registers(text, registers_cfg)

        enriched.append({
            **e,
            "_text": text,
            "_registers": regs,
            "_high_cost": is_high_cost(text, cost_cfg),
        })

    perception = compute_perception(enriched, cfg.get("thresholds", {}))
    actor_poles = compute_actor_poles(enriched)

    entry_points = compute_entry_points(
        enriched,
        cfg.get("entry_point_buckets", {}),
        cost_cfg,
        cfg.get("preferred_entry_point_order", []),
    )

    # country stats for missions
    posture_map = {
        c: p for p, cs in actor_poles.items() for c in cs
    }

    country_stats = defaultdict(lambda: {"topic_count": 0, "posture": None})

    for e in enriched:
        c = e.get("country")
        if not c:
            continue
        country_stats[c]["topic_count"] += 1
        country_stats[c]["posture"] = posture_map.get(c)

    bridge_cfg = cfg.get("thresholds", {}).get("bridge_score", {})
    posture_weights = bridge_cfg.get("posture_weights") or {}
    topic_count_bonus = int(bridge_cfg.get("topic_count_bonus", 1))

    missions = build_missions_to_contact(
        actor_poles, country_stats, posture_weights, topic_count_bonus
    )

    return {
        "label": label,
        "perception_dynamics": perception,
        "actor_poles": actor_poles,
        "operational_translation": {
            "recommended_entry_points": entry_points,
            "missions_to_contact": missions,
        },
        "trace": {
            "entries_used": len(entries),
            "countries_involved": len(country_stats),
        },
    }
