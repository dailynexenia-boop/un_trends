# analysis/layers/block2_5_contextual_signals_core.py
# -*- coding: utf-8 -*-
"""
Block 2.5 - Contextual Signals (CORE)

Responsibilities:
- PURE analytical core (no Streamlit)
- NO file I/O
- Consumes:
  - entries: list[dict] (canonical entries with micro_analysis already present)
  - profiles_by_country: dict[str, dict] (output of Block 2)
  - cfg: dict (block2_5 namespace)
- Produces:
  - results: list[dict] (signals per entry)
  - debug: counters + (optional) per-entry trace

Design goal:
- FALSIFIABLE: always return debug counters even if no results.
"""

from typing import Dict, Any, List, Optional, Tuple


def _safe_get(d: Dict[str, Any], path: str, default=None):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
    return cur if cur is not None else default


def posture_distance(p1: str, p2: str, posture_order: List[str]) -> int:
    if not p1 or not p2:
        return 0
    if p1 not in posture_order or p2 not in posture_order:
        return 0
    return abs(posture_order.index(p1) - posture_order.index(p2))


def posture_deviation_severity(entry_posture: Optional[str], dominant_posture: Optional[str], posture_order: List[str]) -> Optional[str]:
    if not entry_posture or not dominant_posture:
        return None
    if entry_posture == dominant_posture:
        return None

    dist = posture_distance(entry_posture, dominant_posture, posture_order)

    # preserved from your v1 logic
    if entry_posture == "assertive" and dominant_posture != "assertive":
        return "high"
    if dist >= 2:
        return "medium"
    return "low"


def risk_outlier_severity(entry_risk: Optional[str], tolerance: Optional[str]) -> Optional[str]:
    if entry_risk != "high":
        return None

    if tolerance == "low":
        return "high"
    if tolerance == "medium":
        return "medium"
    return None


def topic_out_of_core_severity(entry_topics: List[str], core_topics: List[str]) -> Optional[str]:
    if not entry_topics:
        return None
    core_set = set(core_topics or [])
    out_of_core = [t for t in entry_topics if t not in core_set]
    if not out_of_core:
        return None
    return "medium"


def narrative_novelty_severity(narrative_positioning: Optional[Dict[str, Any]]) -> Optional[str]:
    if not narrative_positioning or not isinstance(narrative_positioning, dict):
        return None

    topic_positions = narrative_positioning.get("topic_positions", {})
    if not topic_positions or not isinstance(topic_positions, dict):
        return None

    for _, flags in topic_positions.items():
        if isinstance(flags, dict) and any(bool(v) for v in flags.values()):
            return "medium"
    return None


def build_rationale(country: str, signals: Dict[str, str]) -> Optional[List[str]]:
    """
    Rationale ONLY if deviation is strong and defensible.
    Templates are fixed (kept from your v1).
    """
    if signals.get("posture_deviation") == "high":
        if "narrative_novelty" in signals:
            return [f"assertive posture unusual for {country}, combined with new narrative framing"]
        return [f"assertive posture unusual for {country}"]

    if "risk_outlier" in signals and "topic_out_of_core" in signals:
        return ["high-risk positioning on a non-core topic"]

    if "narrative_novelty" in signals and len(signals) >= 2:
        return [f"explicit positioning on a topic not usually emphasized by {country}"]

    return None


def _classify_contextual_signal(
    signals: Dict[str, str],
    thresholds: Dict[str, Any]
) -> bool:
    """
    Default logic (your v1):
    - contextual_signal True if:
      - at least 1 "high" signal OR
      - at least 2 total signals
    YAML override:
      thresholds.contextual_signal.min_high (default 1)
      thresholds.contextual_signal.min_total (default 2)
    """
    ctx = (thresholds or {}).get("contextual_signal", {}) if isinstance(thresholds, dict) else {}
    min_high = int(ctx.get("min_high", 1))
    min_total = int(ctx.get("min_total", 2))

    high_count = sum(1 for v in signals.values() if v == "high")
    total = len(signals)

    return (high_count >= min_high) or (total >= min_total)


def analyze_contextual_signals(
    entries: List[Dict[str, Any]],
    profiles_by_country: Dict[str, Dict[str, Any]],
    cfg_block2_5: Dict[str, Any],
    *,
    debug: bool = True,
    include_entry_debug: bool = True
) -> Dict[str, Any]:
    """
    Returns:
    {
      "results": [ ... ],
      "debug": {
          "global": {...},
          "rules": {...},
          "entries": { entry_id: {...} }   # only if include_entry_debug
      }
    }
    """

    posture_order = cfg_block2_5.get("posture_order", None)
    if not isinstance(posture_order, list) or not posture_order:
        posture_order = ["procedural", "passive", "cooperative", "assertive"]

    thresholds = cfg_block2_5.get("thresholds", {}) if isinstance(cfg_block2_5, dict) else {}
    rules_cfg = cfg_block2_5.get("rules", {}) if isinstance(cfg_block2_5, dict) else {}

    ignore_speakers = rules_cfg.get("ignore_speakers", ["unknown"])
    if not isinstance(ignore_speakers, list):
        ignore_speakers = ["unknown"]

    dbg_global = {
        "entries_loaded": len(entries or []),
        "entries_with_country": 0,
        "entries_evaluated": 0,
        "entries_with_any_signal": 0,
        "entries_contextual_true": 0,
        "countries_in_profiles": len(profiles_by_country or {}),
    }

    dbg_rules = {
        "posture_deviation": {"evaluated": 0, "triggered": 0},
        "risk_outlier": {"evaluated": 0, "triggered": 0},
        "topic_out_of_core": {"evaluated": 0, "triggered": 0},
        "narrative_novelty": {"evaluated": 0, "triggered": 0},
    }

    dbg_entries: Dict[str, Any] = {}

    results: List[Dict[str, Any]] = []

    for e in entries or []:
        entry_id = e.get("entry_id") or e.get("id") or e.get("ID")
        if not entry_id:
            # still count loaded, but cannot trace
            continue

        country = _safe_get(e, "speaker_structure.primary_speaker.name", None)
        if country:
            dbg_global["entries_with_country"] += 1

        if not country or str(country).strip().lower() in [str(x).lower() for x in ignore_speakers]:
            if include_entry_debug:
                dbg_entries[str(entry_id)] = {
                    "skipped": True,
                    "reason": "missing_or_ignored_country",
                    "country": country,
                }
            continue

        if country not in (profiles_by_country or {}):
            if include_entry_debug:
                dbg_entries[str(entry_id)] = {
                    "skipped": True,
                    "reason": "country_not_in_profiles",
                    "country": country,
                }
            continue

        profile = profiles_by_country[country]
        micro = e.get("micro_analysis", {}) or {}

        dbg_global["entries_evaluated"] += 1

        signals: Dict[str, str] = {}

        # -----------------------------
        # Posture deviation
        # -----------------------------
        dbg_rules["posture_deviation"]["evaluated"] += 1
        entry_posture = micro.get("diplomatic_posture")
        dominant_posture = _safe_get(profile, "posture.dominant", None)
        sev = posture_deviation_severity(entry_posture, dominant_posture, posture_order)
        if sev:
            signals["posture_deviation"] = sev
            dbg_rules["posture_deviation"]["triggered"] += 1

        # -----------------------------
        # Risk outlier
        # -----------------------------
        dbg_rules["risk_outlier"]["evaluated"] += 1
        risk_level = micro.get("risk_level")
        tolerance = _safe_get(profile, "risk_profile.risk_tolerance", None)
        sev = risk_outlier_severity(risk_level, tolerance)
        if sev:
            signals["risk_outlier"] = sev
            dbg_rules["risk_outlier"]["triggered"] += 1

        # -----------------------------
        # Topic out of core
        # -----------------------------
        dbg_rules["topic_out_of_core"]["evaluated"] += 1
        entry_topics = _safe_get(micro, "topics_analysis.central_topics", []) or []
        if not isinstance(entry_topics, list):
            entry_topics = []
        core_topics = list((_safe_get(profile, "topics.central", {}) or {}).keys())
        sev = topic_out_of_core_severity(entry_topics, core_topics)
        if sev:
            signals["topic_out_of_core"] = sev
            dbg_rules["topic_out_of_core"]["triggered"] += 1

        # -----------------------------
        # Narrative novelty
        # -----------------------------
        dbg_rules["narrative_novelty"]["evaluated"] += 1
        sev = narrative_novelty_severity(micro.get("narrative_positioning"))
        if sev:
            signals["narrative_novelty"] = sev
            dbg_rules["narrative_novelty"]["triggered"] += 1

        if not signals:
            if include_entry_debug:
                dbg_entries[str(entry_id)] = {
                    "skipped": True,
                    "reason": "no_signals",
                    "country": country,
                    "entry_posture": entry_posture,
                    "dominant_posture": dominant_posture,
                    "risk_level": risk_level,
                    "risk_tolerance": tolerance,
                    "entry_topics": entry_topics,
                    "core_topics_sample": core_topics[:10],
                }
            continue

        dbg_global["entries_with_any_signal"] += 1

        contextual_signal = _classify_contextual_signal(signals, thresholds)
        if contextual_signal:
            dbg_global["entries_contextual_true"] += 1

        rationale = build_rationale(country, signals) if contextual_signal else None

        row = {
            "entry_id": str(entry_id),
            "country": country,
            "contextual_signals": signals,
            "contextual_signal": bool(contextual_signal),
            "rationale": rationale,
        }
        results.append(row)

        if include_entry_debug:
            dbg_entries[str(entry_id)] = {
                "skipped": False,
                "country": country,
                "signals": signals,
                "contextual_signal": bool(contextual_signal),
                "entry_posture": entry_posture,
                "dominant_posture": dominant_posture,
                "risk_level": risk_level,
                "risk_tolerance": tolerance,
                "entry_topics": entry_topics,
                "core_topics_sample": core_topics[:10],
                "thresholds_used": {
                    "contextual_signal": {
                        "min_high": int(((thresholds or {}).get("contextual_signal", {}) or {}).get("min_high", 1)),
                        "min_total": int(((thresholds or {}).get("contextual_signal", {}) or {}).get("min_total", 2)),
                    }
                }
            }

    out = {
        "results": results,
        "debug": {
            "global": dbg_global,
            "rules": dbg_rules,
        }
    }
    if include_entry_debug:
        out["debug"]["entries"] = dbg_entries

    return out
