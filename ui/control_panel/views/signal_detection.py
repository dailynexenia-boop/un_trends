# -*- coding: utf-8 -*-
"""
Signal Detection — initiative_terms, mechanism_terms, delegitimization_terms, dashboard_alerts
"""

from pathlib import Path
from typing import Dict, Any
import yaml
import streamlit as st

from ui.control_panel.core.store import load_yaml, save_yaml, snapshot_yaml
from ui.control_panel.core.components import section


def _edit_term_file(
    path: Path,
    title: str,
    description: str,
    snapshot_dir: Path,
):
    section(title, description)
    data = load_yaml(path)

    updated = {}
    changed = False

    for category, terms in data.items():
        if not isinstance(terms, list):
            continue
        raw = st.text_area(
            category,
            value="\n".join(terms),
            height=120,
            key=f"{path.stem}_{category}",
        )
        new_terms = [t.strip() for t in raw.splitlines() if t.strip()]
        updated[category] = new_terms
        if new_terms != terms:
            changed = True

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Save {path.stem}", key=f"save_{path.stem}"):
            save_yaml(path, updated)
            st.success(f"Saved {path.name}")
    with col2:
        if st.button(f"Snapshot {path.stem}", key=f"snap_{path.stem}"):
            ctx = type("C", (), {"snapshot_dir": snapshot_dir})()
            snap, _ = snapshot_yaml(ctx, path, updated)
            st.success(f"Snapshot: {snap.name}")

    if changed:
        st.caption("Unsaved changes in this section.")

    st.divider()


def render(
    config_dir: Path,
    ui_desc: Dict[str, Any],
    project_root: Path,
    snapshot_dir: Path,
):
    st.subheader("Signal Detection")
    st.caption(
        "Term lists used to detect initiatives, mechanisms, delegitimization patterns, "
        "and dashboard alert thresholds."
    )

    # --------------------------------------------------
    # INITIATIVE TERMS
    # --------------------------------------------------
    _edit_term_file(
        config_dir / "initiative_terms.yaml",
        "Initiative terms",
        "Verbs, objects and phrases that signal a state is proposing or launching an initiative.",
        snapshot_dir,
    )

    # --------------------------------------------------
    # MECHANISM TERMS
    # --------------------------------------------------
    _edit_term_file(
        config_dir / "mechanism_terms.yaml",
        "Mechanism terms",
        "Terms identifying judicial, UN and secretariat mechanisms invoked in statements.",
        snapshot_dir,
    )

    # --------------------------------------------------
    # DELEGITIMIZATION TERMS
    # --------------------------------------------------
    _edit_term_file(
        config_dir / "delegitimization_terms.yaml",
        "Delegitimization terms",
        "Expressions used to contest or undermine the legitimacy of a mandate or process.",
        snapshot_dir,
    )

    # --------------------------------------------------
    # DASHBOARD ALERTS
    # --------------------------------------------------
    section(
        "Dashboard alert thresholds",
        "Controls when the dashboard raises a spike, high-risk burst, or watch-flag alert.",
    )

    alerts_path = config_dir / "dashboard_alerts.yaml"
    cfg = load_yaml(alerts_path)
    alerts = cfg.get("alerts", {})

    st.markdown("#### Spike detection")
    col1, col2, col3 = st.columns(3)
    with col1:
        spike_window = st.number_input(
            "Spike window (days)",
            min_value=1,
            value=int(alerts.get("spike_window_days", 2)),
            help="Number of recent days to measure activity.",
        )
    with col2:
        baseline_days = st.number_input(
            "Baseline period (days)",
            min_value=1,
            value=int(alerts.get("baseline_days", 14)),
            help="Reference window for computing average activity.",
        )
    with col3:
        spike_mult = st.number_input(
            "Spike multiplier",
            min_value=0.1,
            step=0.1,
            value=float(alerts.get("spike_multiplier", 1.8)),
            help="Alert fires when recent rate exceeds baseline × multiplier.",
        )

    st.markdown("#### High-risk burst")
    col4, col5 = st.columns(2)
    with col4:
        hr_window = st.number_input(
            "High-risk window (days)",
            min_value=1,
            value=int(alerts.get("high_risk_window_days", 3)),
        )
    with col5:
        hr_min = st.number_input(
            "Minimum high-risk entries",
            min_value=1,
            value=int(alerts.get("high_risk_min_count", 5)),
        )

    st.markdown("#### Watch-flag burst")
    col6, col7 = st.columns(2)
    with col6:
        watch_window = st.number_input(
            "Watch window (days)",
            min_value=1,
            value=int(alerts.get("watch_window_days", 3)),
        )
    with col7:
        watch_min = st.number_input(
            "Minimum watch-flag entries",
            min_value=1,
            value=int(alerts.get("watch_min_count", 6)),
        )

    st.markdown("#### Actor repetition")
    col8, col9 = st.columns(2)
    with col8:
        actor_window = st.number_input(
            "Actor repeat window (days)",
            min_value=1,
            value=int(alerts.get("actor_repeat_window_days", 7)),
        )
    with col9:
        actor_min = st.number_input(
            "Min high-risk entries per actor",
            min_value=1,
            value=int(alerts.get("actor_repeat_high_risk_min", 3)),
        )

    st.markdown("#### Session alert triggers")
    st.caption("Comma-separated levels that trigger each alert type.")

    def list_to_str(v):
        return ", ".join(v) if isinstance(v, list) else str(v or "")

    def str_to_list(s):
        return [x.strip() for x in s.split(",") if x.strip()]

    spillover = st.text_input(
        "Spillover risk triggers",
        value=list_to_str(alerts.get("spillover_risk_triggers", ["high"])),
    )
    fragmentation = st.text_input(
        "Fragmentation triggers",
        value=list_to_str(alerts.get("fragmentation_triggers", ["high"])),
    )
    bridge_bad = st.text_input(
        "Bridge potential (bad) triggers",
        value=list_to_str(alerts.get("bridge_potential_bad", ["low"])),
    )

    updated_alerts = {
        "alerts": {
            "spike_window_days": int(spike_window),
            "baseline_days": int(baseline_days),
            "spike_multiplier": float(spike_mult),
            "high_risk_window_days": int(hr_window),
            "high_risk_min_count": int(hr_min),
            "watch_window_days": int(watch_window),
            "watch_min_count": int(watch_min),
            "actor_repeat_window_days": int(actor_window),
            "actor_repeat_high_risk_min": int(actor_min),
            "spillover_risk_triggers": str_to_list(spillover),
            "fragmentation_triggers": str_to_list(fragmentation),
            "bridge_potential_bad": str_to_list(bridge_bad),
        }
    }

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Save alert thresholds"):
            save_yaml(alerts_path, updated_alerts)
            st.success("Saved dashboard_alerts.yaml")
    with col_b:
        if st.button("Snapshot alert thresholds"):
            ctx = type("C", (), {"snapshot_dir": snapshot_dir})()
            snap, _ = snapshot_yaml(ctx, alerts_path, updated_alerts)
            st.success(f"Snapshot: {snap.name}")
