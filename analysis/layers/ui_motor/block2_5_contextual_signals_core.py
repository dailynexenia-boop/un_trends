# -*- coding: utf-8 -*-
"""
Block 2.5 — Contextual Signals (Refactored)

Detects contextual deviations at entry level relative to
country profiles (Block 2).

Principles:
- YAML-driven doctrine (block2_5)
- Pure analytical logic
- File I/O only in wrapper (this script acts as batch runner)
"""

import json
from pathlib import Path

from analysis.config_loader import load_block4_config


# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
FEATURES_DIR = BASE_DIR / "features"
PROFILES_DIR = BASE_DIR / "profiles"
OUTPUT_DIR = BASE_DIR / "contextual_signals"

OUTPUT_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# HELPERS (PURE)
# --------------------------------------------------

def posture_distance(p1, p2, order):
    if p1 not in order or p2 not in order:
        return 0
    return abs(order.index(p1) - order.index(p2))


def posture_deviation_severity(entry_posture, dominant_posture, cfg):
    if not entry_posture or entry_posture == dominant_posture:
        return None

    order = cfg.get("posture_order", [])
    rules = cfg.get("deviation_rules", {}).get("posture_deviation", {})

    # High: assertive outlier
    if (
        entry_posture == "assertive"
        and dominant_posture != "assertive"
        and rules.get("assertive_outlier", {}).get("severity") == "high"
    ):
        return "high"

    # Medium: distance threshold
    dist = posture_distance(entry_posture, dominant_posture, order)
    medium_dist = rules.get("distance_thresholds", {}).get("medium", 2)

    if dist >= medium_dist:
        return "medium"

    return "low"


def risk_outlier_severity(entry_risk, tolerance, cfg):
    if entry_risk != "high":
        return None

    rules = cfg.get("deviation_rules", {}).get("risk_outlier", {})

    if tolerance == "low":
        return rules.get("high_risk_on_low_tolerance", "high")

    if tolerance == "medium":
        return rules.get("high_risk_on_medium_tolerance", "medium")

    return None


def topic_out_of_core_severity(entry_topics, core_topics, cfg):
    if not entry_topics:
        return None

    out = [t for t in entry_topics if t not in core_topics]
    if not out:
        return None

    return cfg.get("deviation_rules", {}) \
              .get("topic_out_of_core", {}) \
              .get("severity", "medium")


def narrative_novelty_severity(narrative_positioning, cfg):
    if not narrative_positioning:
        return None

    topic_positions = narrative_positioning.get("topic_positions", {})
    if not topic_positions:
        return None

    for _, flags in topic_positions.items():
        if any(flags.values()):
            return cfg.get("deviation_rules", {}) \
                      .get("narrative_novelty", {}) \
                      .get("severity", "medium")

    return None


def build_rationale(country, signals, cfg):
    """
    Builds rationale ONLY for strong / explainable deviations.
    Templates are YAML-driven.
    """

    templates = cfg.get("rationale_templates", {})

    if signals.get("posture_deviation") == "high":
        if "narrative_novelty" in signals:
            tmpl = templates.get("assertive_plus_novelty")
        else:
            tmpl = templates.get("assertive_only")

        if tmpl:
            return [t.format(country=country) for t in tmpl]

    if "risk_outlier" in signals and "topic_out_of_core" in signals:
        tmpl = templates.get("risk_on_non_core")
        if tmpl:
            return tmpl

    if "narrative_novelty" in signals and len(signals) >= 2:
        tmpl = templates.get("novelty_multi")
        if tmpl:
            return [t.format(country=country) for t in tmpl]

    return None


# --------------------------------------------------
# MAIN PROCESS (BATCH WRAPPER)
# --------------------------------------------------

def process(session_id: str):

    # Load config
    cfg = load_block4_config(
        BASE_DIR.parents[1] / "config" / "block4.yaml"
    )
    block_cfg = cfg.block2_5

    entries_path = FEATURES_DIR / f"{session_id}_entries_micro_v1.jsonl"
    profiles_path = PROFILES_DIR / f"{session_id}_country_profiles_v1.json"
    output_path = OUTPUT_DIR / f"{session_id}_contextual_signals_v1_1.jsonl"

    # Load profiles
    with open(profiles_path, encoding="utf-8") as f:
        profiles = {p["country"]: p for p in json.load(f)}

    agg_rules = block_cfg.get("aggregation_rules", {}) \
                         .get("contextual_signal", {})

    with open(entries_path, encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        for line in fin:
            entry = json.loads(line)

            country = (
                entry.get("speaker_structure", {})
                .get("primary_speaker", {})
                .get("name")
            )

            if not country or country not in profiles:
                continue

            profile = profiles[country]
            micro = entry.get("micro_analysis", {})

            signals = {}

            # -----------------------------
            # Posture deviation
            # -----------------------------
            sev = posture_deviation_severity(
                micro.get("diplomatic_posture"),
                profile["posture"]["dominant"],
                block_cfg
            )
            if sev:
                signals["posture_deviation"] = sev

            # -----------------------------
            # Risk outlier
            # -----------------------------
            sev = risk_outlier_severity(
                micro.get("risk_level"),
                profile["risk_profile"]["risk_tolerance"],
                block_cfg
            )
            if sev:
                signals["risk_outlier"] = sev

            # -----------------------------
            # Topic out of core
            # -----------------------------
            sev = topic_out_of_core_severity(
                micro.get("topics_analysis", {}).get("central_topics", []),
                profile["topics"]["central"].keys(),
                block_cfg
            )
            if sev:
                signals["topic_out_of_core"] = sev

            # -----------------------------
            # Narrative novelty
            # -----------------------------
            sev = narrative_novelty_severity(
                micro.get("narrative_positioning"),
                block_cfg
            )
            if sev:
                signals["narrative_novelty"] = sev

            if not signals:
                continue

            # -----------------------------
            # Aggregation logic
            # -----------------------------
            high_count = sum(1 for v in signals.values() if v == "high")

            contextual_signal = (
                high_count >= agg_rules.get("high_severity_min", 1)
                or len(signals) >= agg_rules.get("total_signals_min", 2)
            )

            rationale = None
            if contextual_signal:
                rationale = build_rationale(country, signals, block_cfg)

            fout.write(json.dumps({
                "entry_id": entry["entry_id"],
                "country": country,
                "contextual_signals": signals,
                "contextual_signal": contextual_signal,
                "rationale": rationale
            }, ensure_ascii=False) + "\n")

    print(f"[OK] Block 2.5 contextual signals generated → {output_path}")


# --------------------------------------------------
# CLI
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python block2_5_contextual_signals_core.py <SESSION_ID>")
    else:
        process(sys.argv[1])
