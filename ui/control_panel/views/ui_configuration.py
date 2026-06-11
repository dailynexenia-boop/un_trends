# -*- coding: utf-8 -*-
"""
UI CONFIG — Block 2.5 & Block 3 (FINAL, BLOCK-4-ALIGNED)

- Same save semantics as Block 4
- YAML backup (_history)
- Human-readable thresholds
- Analytical parameters only
"""

from pathlib import Path
from datetime import datetime
import shutil
import yaml
import streamlit as st

from ui.control_panel.core.components import section

# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "config" / "block4.yaml"

# ==================================================
# YAML HELPERS (BLOCK 4 IDENTICAL)
# ==================================================

def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_yaml_with_backup(path: Path, content: dict):
    history_dir = path.parent / "_history"
    history_dir.mkdir(exist_ok=True)

    if path.exists():
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        shutil.copy2(path, history_dir / f"{path.name}.{ts}.bak")

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(content, f, allow_unicode=True, sort_keys=False)

# ==================================================
# PAGE
# ==================================================

def render(*args, **kwargs):
    st.subheader("Analytical Configuration")
    st.caption("Analytical doctrine (reload required after save)")

    cfg = load_yaml(CONFIG_PATH)
    updated = {}

    b25 = cfg.get("block2_5", {})
    b3 = cfg.get("block3", {})

    # ==================================================
    # BLOCK 2.5 — CONTEXTUAL SIGNALS
    # ==================================================

    section(
        "Contextual Signals",
        "Detects contextual deviations from country posture baselines."
    )

    st.markdown("### Posture reference order")
    st.caption(
        "Defines analytical distance between postures.\n"
        "Used to detect contextual deviation from the country baseline."
    )

    posture_order = st.text_area(
        "Ordered postures (one per line)",
        value="\n".join(b25.get("posture_order", [])),
        height=120,
    )

    st.divider()
    st.markdown("### Contextual signal activation thresholds")

    st.info(
        "A contextual signal is raised when **both conditions** are met.\n"
        "Increase values to reduce sensitivity."
    )

    thresholds_25 = b25.get("thresholds", {}).get("contextual_signal", {})

    col1, col2 = st.columns(2)
    with col1:
        min_high = st.number_input(
            "Minimum high-intensity deviations",
            min_value=0,
            value=int(thresholds_25.get("min_high", 1)),
        )

    with col2:
        min_total = st.number_input(
            "Minimum total deviations",
            min_value=0,
            value=int(thresholds_25.get("min_total", 2)),
        )

    st.divider()
    st.markdown("### Exclusion rules")
    st.caption("Ignored speakers never contribute to contextual signals.")

    ignore_speakers = st.text_area(
        "Ignored speakers (one per line)",
        value="\n".join(
            b25.get("rules", {}).get("ignore_speakers", [])
        ),
        height=100,
    )

    updated["block2_5"] = {
        "posture_order": [
            p.strip() for p in posture_order.splitlines() if p.strip()
        ],
        "thresholds": {
            "contextual_signal": {
                "min_high": int(min_high),
                "min_total": int(min_total),
            }
        },
        "rules": {
            "ignore_speakers": [
                s.strip() for s in ignore_speakers.splitlines() if s.strip()
            ]
        },
    }

    # ==================================================
    # BLOCK 3 — REGIONAL PROFILES
    # ==================================================

    st.divider()

    section(
        "Regional Profiles",
        "Aggregates country profiles into regional analytical patterns."
    )

    st.markdown("### Regional aggregation thresholds")
    st.info(
        "These thresholds define when a regional pattern becomes analytically meaningful.\n"
        "Higher values = stricter regional consensus."
    )

    thresholds_3 = b3.get("thresholds", {})

    col1, col2 = st.columns(2)
    with col1:
        regional_concern_ratio = st.number_input(
            "Regional concern ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            value=float(thresholds_3.get("regional_concern_ratio", 0.3)),
        )

    with col2:
        leaders_count = st.number_input(
            "Minimum number of regional leaders",
            min_value=1,
            value=int(thresholds_3.get("leaders_count", 3)),
        )

    col3, col4 = st.columns(2)
    with col3:
        min_activity = st.number_input(
            "Minimum country activity",
            min_value=0,
            value=int(thresholds_3.get("min_activity", 2)),
        )

    with col4:
        posture_distance = st.number_input(
            "Posture deviation distance",
            min_value=0,
            value=int(thresholds_3.get("posture_deviation_distance", 2)),
        )

    st.divider()
    st.markdown("### Classification rules")

    ignore_missing_region = st.checkbox(
        "Ignore countries without regional attribution",
        value=bool(
            b3.get("rules", {}).get("ignore_missing_region", True)
        ),
    )

    updated["block3"] = {
        "thresholds": {
            "regional_concern_ratio": float(regional_concern_ratio),
            "leaders_count": int(leaders_count),
            "min_activity": int(min_activity),
            "posture_deviation_distance": int(posture_distance),
        },
        "rules": {
            "ignore_missing_region": ignore_missing_region
        },
    }

    # ==================================================
    # SAVE
    # ==================================================

    st.divider()
    if st.button("💾 Save analytical configuration"):
        merged = cfg.copy()
        merged.update(updated)
        save_yaml_with_backup(CONFIG_PATH, merged)
        st.success("Configuration saved successfully. Reload to apply.")
