# -*- coding: utf-8 -*-
"""
Registers — Combined Registers Page (FINAL)

Includes:
- Topic Position Registers editor
- Speaker Structure editor

No doctrine. Pure reference layers.
"""

from pathlib import Path
from datetime import datetime
import shutil
import yaml
import subprocess
import streamlit as st

# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"

TOPIC_REGISTERS_PATH = CONFIG_DIR / "topic_position_registers.yaml"
COUNTRIES_PATH = CONFIG_DIR / "countries.yaml"
INSTITUTIONS_PATH = CONFIG_DIR / "institutions.yaml"
ALIGNMENT_GROUPS_PATH = CONFIG_DIR / "alignment_groups.yaml"

# ==================================================
# YAML HELPERS
# ==================================================

def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml_with_backup(path: Path, content):
    history_dir = path.parent / "_history"
    history_dir.mkdir(exist_ok=True)

    if path.exists():
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        shutil.copy2(path, history_dir / f"{path.name}.{ts}.bak")

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(content, f, allow_unicode=True, sort_keys=False)

# ==================================================
# GENERIC UI COMPONENT
# ==================================================

def render_string_list(label: str, values: list, key_prefix: str):
    text = st.text_area(
        label,
        value="\n".join(values or []),
        height=120,
        key=f"{key_prefix}_list",
    )
    return [v.strip() for v in text.splitlines() if v.strip()]

# ==================================================
# PAGE
# ==================================================

def render(*args, **kwargs):
    st.subheader("Registers")
    st.caption(
        "Reference structures used across the system. "
        "These layers are declarative and require recompute after changes."
    )

    # ==================================================
    # TOPIC REGISTERS
    # ==================================================

    st.markdown("## Topic Position Registers")

    registers = load_yaml(TOPIC_REGISTERS_PATH)
    updated_topics = {}

    for topic, positions in registers.items():
        with st.expander(f"Topic — {topic}", expanded=False):
            new_positions = {}

            for position, keywords in positions.items():
                st.markdown(f"**Position: `{position}`**")

                new_keywords = render_string_list(
                    "Keywords (one per line)",
                    keywords,
                    key_prefix=f"{topic}_{position}",
                )

                new_positions[position] = new_keywords
                st.markdown("---")

            new_position = st.text_input(
                f"Add new position to {topic}",
                key=f"{topic}_new_position",
            )

            if new_position and new_position not in new_positions:
                new_positions[new_position] = []

            delete_topic = st.checkbox(
                f"Delete topic {topic}",
                key=f"delete_topic_{topic}",
            )

            if not delete_topic:
                updated_topics[topic] = new_positions

    new_topic = st.text_input("Add new topic (e.g. CLIMATE_CHANGE)")
    if new_topic and new_topic not in updated_topics:
        updated_topics[new_topic] = {}

    if st.button("💾 Save Topic Registers"):
        save_yaml_with_backup(TOPIC_REGISTERS_PATH, updated_topics)
        st.warning("Canonical dataset is now outdated. Full recompute required.")

    st.divider()

    # ==================================================
    # SPEAKER STRUCTURE
    # ==================================================

    st.markdown("## Speaker Structure")

    countries = load_yaml(COUNTRIES_PATH)
    institutions = load_yaml(INSTITUTIONS_PATH)
    alignment_groups = load_yaml(ALIGNMENT_GROUPS_PATH)

    updated_countries = {}
    updated_institutions = []
    updated_alignment_groups = []

    with st.expander("Countries", expanded=True):
        search = st.text_input(
            "Search country (name or alias)",
            placeholder="Type to filter…",
        )

        for country in sorted(countries.keys()):
            cfg = countries[country]
            aliases = cfg.get("aliases", [])

            haystack = " ".join([country] + aliases).lower()
            if search and search.lower() not in haystack:
                continue

            with st.expander(country, expanded=False):
                new_aliases = render_string_list(
                    "Aliases",
                    aliases,
                    key_prefix=f"{country}_aliases",
                )

                regional_group = st.text_input(
                    "Regional group",
                    value=cfg.get("regional_group", ""),
                    key=f"{country}_regional_group",
                )

                delete_country = st.checkbox(
                    f"Delete {country}",
                    key=f"delete_country_{country}",
                )

                if not delete_country:
                    updated_countries[country] = {
                        "aliases": new_aliases,
                        "regional_group": regional_group,
                    }

        new_country = st.text_input("Add new country (e.g. South Sudan)")
        if new_country and new_country not in updated_countries:
            updated_countries[new_country] = {
                "aliases": [],
                "regional_group": "",
            }

    with st.expander("Institutions", expanded=False):
        updated_institutions = render_string_list(
            "Institutions",
            institutions,
            key_prefix="institutions",
        )

    with st.expander("Alignment groups", expanded=False):
        updated_alignment_groups = render_string_list(
            "Alignment groups",
            alignment_groups,
            key_prefix="alignment_groups",
        )

    if st.button("💾 Save Speaker Structure"):
        save_yaml_with_backup(COUNTRIES_PATH, updated_countries)
        save_yaml_with_backup(INSTITUTIONS_PATH, updated_institutions)
        save_yaml_with_backup(ALIGNMENT_GROUPS_PATH, updated_alignment_groups)

        st.warning("Canonical dataset is now outdated. Full recompute required.")

    if st.button("🔁 Recompute canonical (ALL)"):
        subprocess.run(
            ["python", "analysis/recompute_canonical.py", "--all"],
            cwd=PROJECT_ROOT,
        )
        st.success("Recompute completed successfully.")
