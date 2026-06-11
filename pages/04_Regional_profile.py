# -*- coding: utf-8 -*-
"""
UI — Block 3 : Regional Profiles

- Derived ONLY from Block 2 country profiles
- Regional norm made explicit
- Click on country → inline country details (no page routing)
"""

# ==================================================
# BOOTSTRAP
# ==================================================

import sys
import json
import ast
from pathlib import Path
from collections import defaultdict
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from shared.bootstrap import PROJECT_ROOT
from analysis.layers.block2_country_profiles_core import analyze_country_profiles
from analysis.layers.block3_regional_summary_core import analyze_regional_summary
from analysis.config_loader import load_block4_config


# ==================================================
# PATHS
# ==================================================

CANONICAL_PATH = PROJECT_ROOT / "canonical" / "canonical.jsonl"
CFG_PATH = PROJECT_ROOT / "config" / "block4.yaml"


# ==================================================
# SESSION STATE
# ==================================================

if "selected_region" not in st.session_state:
    st.session_state.selected_region = None

if "selected_country" not in st.session_state:
    st.session_state.selected_country = None


# ==================================================
# CONFIG NORMALIZATION
# ==================================================

def normalize_block2_cfg(cfg):
    thresholds = cfg.block2.get("thresholds", {})
    for k in ["volatility", "risk_tolerance", "diversity"]:
        if isinstance(thresholds.get(k), str):
            thresholds[k] = ast.literal_eval(thresholds[k])
    return cfg


# ==================================================
# LOADERS
# ==================================================

@st.cache_data
def load_canonical(path: Path):
    entries = []
    by_conf = defaultdict(list)
    dates_by_conf = defaultdict(set)

    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            conf = e.get("conference")
            date = e.get("date")
            if not conf:
                continue
            entries.append(e)
            by_conf[conf].append(e)
            if date:
                dates_by_conf[conf].add(date)

    return entries, by_conf, {c: sorted(d) for c, d in dates_by_conf.items()}


# ==================================================
# PAGE
# ==================================================

st.set_page_config("Regional Profiles", layout="wide")
st.title("Regional Profiles")
st.caption("Regional baselines derived from country-level behavior")

entries, entries_by_conf, dates_by_conf = load_canonical(CANONICAL_PATH)
cfg = normalize_block2_cfg(load_block4_config(CFG_PATH))


# ==================================================
# SCOPE
# ==================================================

st.markdown("## Scope")

conf = st.selectbox("Conference", sorted(entries_by_conf.keys()))
available_dates = dates_by_conf.get(conf, [])

time_mode = st.radio(
    "Date filter",
    ["All dates", "Single day", "Date range"],
    horizontal=True
)

selected_date = None
date_range = None

if time_mode == "Single day" and available_dates:
    selected_date = st.selectbox("Date", available_dates)

elif time_mode == "Date range" and available_dates:
    start = st.selectbox("From", available_dates, 0)
    end = st.selectbox("To", available_dates, len(available_dates) - 1)
    date_range = (min(start, end), max(start, end))


def filter_entries():
    out = []
    for e in entries_by_conf[conf]:
        d = e.get("date")
        if time_mode == "All dates":
            out.append(e)
        elif time_mode == "Single day" and d == selected_date:
            out.append(e)
        elif time_mode == "Date range" and d and date_range[0] <= d <= date_range[1]:
            out.append(e)
    return out


filtered_entries = filter_entries()
st.caption(f"{len(filtered_entries)} interventions selected")

if not filtered_entries:
    st.warning("No interventions in this scope.")
    st.stop()


# ==================================================
# BLOCK 2 → COUNTRY PROFILES
# ==================================================

profiles = analyze_country_profiles(filtered_entries, cfg)
profiles_by_country = {p["country"]: p for p in profiles}


# ==================================================
# BLOCK 3 → REGIONAL SUMMARY
# ==================================================

regional_summaries = analyze_regional_summary(profiles, cfg)

if not regional_summaries:
    st.warning("No regional data available.")
    st.stop()


# ==================================================
# REGIONAL CARDS
# ==================================================

st.markdown("## Regions")

cols = st.columns(3)

for i, r in enumerate(regional_summaries):
    with cols[i % 3]:
        with st.container(border=True):
            region = r["region"]

            st.markdown(f"### {region}")
            st.caption(
                f"{len(r['countries']['leaders'])} leaders · "
                f"{len(r['countries']['dissident'])} dissidents"
            )

            st.caption(
                f"Dominant style: {r['dominant_posture']}"
            )

            if st.button("🔍 View region", key=f"region_{region}"):
                st.session_state.selected_region = region
                st.session_state.selected_country = None


# ==================================================
# REGION DETAILS
# ==================================================

if st.session_state.selected_region:
    st.divider()
    region = next(
        r for r in regional_summaries
        if r["region"] == st.session_state.selected_region
    )

    st.markdown(f"## Region details — {region['region']}")

    # -------------------------
    # REGIONAL NORM
    # -------------------------

    POSTURE_EXPLAIN = {
        "passive": "Mostly neutral or minimal statements",
        "procedural": "Focuses on process and formal rules",
        "cooperative": "Emphasizes cooperation and consensus",
        "normative": "Refers to law, norms and principles",
        "assertive": "Strongly defends positions or criticizes others",
    }

    st.markdown("### Regional norm")

    st.markdown(
        f"**Dominant speaking style:** {region['dominant_posture']}  \n"
        f"<span style='color:#666'>"
        f"{POSTURE_EXPLAIN.get(region['dominant_posture'], '')}"
        f"</span>",
        unsafe_allow_html=True
    )

    if region["regional_concerns"]:
        st.markdown("**Shared regional priorities:**")
        for t in region["regional_concerns"]:
            st.write(f"- {t}")
    else:
        st.caption("No clearly dominant shared priorities.")

    st.divider()

    # -------------------------
    # COUNTRIES POSITIONING
    # -------------------------

    st.markdown("### Countries positioning")

    col_l, col_a, col_d = st.columns(3)

    def country_button(country, key):
        if st.button(country, key=key):
            st.session_state.selected_country = country

    with col_l:
        st.markdown("#### Leaders")
        for c in region["countries"]["leaders"]:
            country_button(c, f"leader_{c}")

    with col_a:
        st.markdown("#### Aligned")
        for c in region["countries"]["aligned"]:
            country_button(c, f"aligned_{c}")

    with col_d:
        st.markdown("#### Dissident")
        for d in region["countries"]["dissident"]:
            c = d["country"]
            if st.button(c, key=f"diss_{c}"):
                st.session_state.selected_country = c
            st.caption(d["deviation"]["detail"])

    # ==================================================
    # COUNTRY DETAILS (INLINE, NO ROUTING)
    # ==================================================

    if st.session_state.selected_country:
        st.divider()
        country = st.session_state.selected_country
        profile = profiles_by_country.get(country)

        if not profile:
            st.warning("Country profile not available.")
        else:
            st.markdown(f"## Country details — {country}")

            c1, c2, c3 = st.columns(3)

            def participation_level(n):
                if n <= 2:
                    return "low"
                if n <= 5:
                    return "medium"
                return "high"

            with c1:
                st.metric(
                    "Participation",
                    participation_level(profile["activity"]["interventions_count"]),
                    help=f"{profile['activity']['interventions_count']} statements"
                )

            with c2:
                st.metric(
                    "Speaking style",
                    profile["posture"]["dominant"],
                    help=POSTURE_EXPLAIN.get(profile["posture"]["dominant"], "")
                )

            with c3:
                st.metric(
                    "Political risk",
                    profile["risk_profile"]["risk_tolerance"]
                )

            st.divider()

            st.markdown("### Main themes")
            for t, n in sorted(
                profile["topics"]["central"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]:
                st.write(f"- **{t}** ({n} mentions)")
