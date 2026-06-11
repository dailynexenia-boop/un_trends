# -*- coding: utf-8 -*-
"""
Analysis Logic — Micro Analysis (FINAL)

- Edits the real micro_analysis.yaml
- Full doctrinal editor (except text_processing & signal_structure)
- Automatic backup before save
- Triggers full recompute
"""

from pathlib import Path
from datetime import datetime
import shutil
import yaml
import subprocess
import streamlit as st

# ==================================================
# PATHS (adapted to ui/control_panel/views)
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"
MICRO_YAML_PATH = CONFIG_DIR / "micro_analysis.yaml"

# ==================================================
# YAML HELPERS
# ==================================================

def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml_with_backup(path: Path, content: dict):
    history_dir = path.parent / "_history"
    history_dir.mkdir(exist_ok=True)

    if path.exists():
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        shutil.copy2(path, history_dir / f"{path.name}.{ts}.bak")

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            content,
            f,
            allow_unicode=True,
            sort_keys=False,
        )

# ==================================================
# GENERIC UI COMPONENTS
# ==================================================

def render_string_list(title: str, values: list, help_text: str = "") -> list:
    st.markdown(f"**{title}**")
    if help_text:
        st.caption(help_text)

    text = st.text_area(
        f"{title} (one per line)",
        value="\n".join(values or []),
        height=120,
        key=f"{title}_list",
    )

    return [v.strip() for v in text.splitlines() if v.strip()]


def render_levels_section(title: str, cfg: dict) -> dict:
    st.subheader(title)

    priority = list(cfg.get("priority", []))
    mapping = dict(cfg.get("mapping", {}))
    default = cfg.get("default", "")

    st.markdown("**Priority order**")
    priority = st.multiselect(
        "Evaluation order (top = first)",
        options=priority,
        default=priority,
        key=f"{title}_priority",
    )

    new_level = st.text_input("Add new level", key=f"{title}_new_level")
    if new_level and new_level not in priority:
        priority.append(new_level)
        mapping[new_level] = {"keywords": []}

    st.markdown("**Keywords per level**")
    new_mapping = {}
    for level in priority:
        kws = mapping.get(level, {}).get("keywords", [])
        text = st.text_area(
            f"{level} keywords",
            value="\n".join(kws),
            key=f"{title}_{level}_kws",
        )
        new_mapping[level] = {
            "keywords": [k.strip() for k in text.splitlines() if k.strip()]
        }

    new_default = st.text_input(
        "Default value",
        value=str(default),
        key=f"{title}_default",
    )

    return {
        "priority": priority,
        "mapping": new_mapping,
        "default": new_default,
    }

# ==================================================
# PAGE
# ==================================================

def render(*args, **kwargs):
    st.title("Micro Analysis parameters")

    raw = load_yaml(MICRO_YAML_PATH)
    micro = raw.get("micro_analysis", raw)

    updated = {}

    # ==================================================
    # LEVEL-BASED SECTIONS
    # ==================================================

    with st.expander("Discursive gestures", expanded=True):
        updated["discursive_gestures"] = render_levels_section(
            "Discursive gestures",
            micro["discursive_gestures"],
        )

    with st.expander("Diplomatic posture", expanded=False):
        updated["diplomatic_posture"] = render_levels_section(
            "Diplomatic posture",
            micro["diplomatic_posture"],
        )

    with st.expander("Explicitness", expanded=False):
        updated["explicitness"] = render_levels_section(
            "Explicitness",
            micro["explicitness"],
        )

    with st.expander("Risk", expanded=False):
        updated["risk"] = render_levels_section(
            "Risk",
            micro["risk"],
        )

    # ==================================================
    # TOPICS
    # ==================================================

    with st.expander("Topics", expanded=True):
        topics = micro["topics"]

        st.markdown("**Detection source**")
        st.code(topics["detection"]["source"])

        sensitivity = topics.get("sensitivity", {})
        sensitivity["enforced_signal_match"] = render_string_list(
            "Sensitive topics",
            sensitivity.get("enforced_signal_match", []),
            "Topics requiring explicit signal match",
        )

        central = topics.get("central", {})
        central["max_items"] = st.number_input(
            "Central topics max",
            value=central.get("max_items", 1),
            step=1,
        )

        secondary = topics.get("secondary", {})
        secondary["max_items"] = st.number_input(
            "Secondary topics max",
            value=secondary.get("max_items", 5),
            step=1,
        )

        updated["topics"] = {
            "detection": topics["detection"],
            "sensitivity": sensitivity,
            "central": central,
            "secondary": secondary,
        }

    # ==================================================
    # DIPLOMATIC ACTS
    # ==================================================

    with st.expander("Diplomatic acts", expanded=False):
        acts_cfg = micro["diplomatic_acts"]
        enabled = st.toggle(
            "Enable diplomatic acts detection",
            value=acts_cfg.get("enabled", True),
        )

        new_acts = {}
        for act, cfg_act in acts_cfg.get("acts", {}).items():
            st.markdown(f"**{act}**")
            kws = cfg_act.get("keywords", [])
            text = st.text_area(
                f"{act} keywords",
                value="\n".join(kws),
                key=f"act_{act}",
            )
            new_acts[act] = {
                "keywords": [k.strip() for k in text.splitlines() if k.strip()]
            }

        new_act = st.text_input("Add new diplomatic act")
        if new_act and new_act not in new_acts:
            new_acts[new_act] = {"keywords": []}

        updated["diplomatic_acts"] = {
            "enabled": enabled,
            "acts": new_acts,
        }

    # ==================================================
    # WATCH FLAG
    # ==================================================

    with st.expander("Watch flag", expanded=False):
        wf = micro["watch_flag"]
        wf_enabled = st.toggle(
            "Enable watch flag",
            value=wf.get("enabled", False),
        )

        triggers = wf.get("triggers", {})

        triggers["explicitness"] = render_string_list(
            "Explicitness triggers",
            triggers.get("explicitness", []),
        )

        triggers["risk"] = render_string_list(
            "Risk triggers",
            triggers.get("risk", []),
        )

        triggers["posture"] = render_string_list(
            "Posture triggers",
            triggers.get("posture", []),
        )

        topics_cfg = triggers.get("topics", {})
        topics_cfg["include"] = render_string_list(
            "Topic triggers",
            topics_cfg.get("include", []),
        )
        triggers["topics"] = topics_cfg

        acts_cfg = triggers.get("diplomatic_acts", {})
        acts_cfg["any"] = st.checkbox(
            "Trigger on any diplomatic act",
            value=acts_cfg.get("any", False),
        )
        triggers["diplomatic_acts"] = acts_cfg

        updated["watch_flag"] = {
            "enabled": wf_enabled,
            "triggers": triggers,
        }

    st.divider()

    # ==================================================
    # ACTIONS
    # ==================================================

    if st.button("Save Micro Analysis configuration"):
        save_yaml_with_backup(
            MICRO_YAML_PATH,
            {"micro_analysis": updated},
        )
        st.warning("Canonical dataset is now outdated. Full recompute required.")

    if st.button("Recompute canonical (ALL)"):
        subprocess.run(
            ["python", "analysis/recompute_canonical.py", "--all"],
            cwd=PROJECT_ROOT,
        )
        st.success("Recompute completed successfully.")
