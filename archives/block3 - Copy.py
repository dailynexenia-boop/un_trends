# -*- coding: utf-8 -*-
"""
UI — Block 3 : Regional Profiles

Principles:
- Derived ONLY from Block 2 country profiles
- No sidebar
- Cards overview + drill-down
- Plain language, analyst-grade
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

from analysis.layers.block2_country_profiles_core import analyze_country_profiles
from analysis.layers.block3_regional_summary_core import analyze_regional_summary
from analysis.config_loader import load_block4_config


# ==================================================
# PATHS
# ==================================================

CANONICAL_PATH = PROJECT_ROOT / "canonical" / "canonical.jsonl"
CFG_PATH = PROJECT_ROOT / "config" / "block4.yaml"


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

st.set_page_config("Regional Profiles — Block 3", layout="wide")
st.title("Regional Profiles")
st.caption("Regional baselines derived from country-level behavior")

entries, entries_by_conf, dates_by_conf = load_canonical(CANONICAL_PATH)
cfg = normalize_block2_cfg(load_block4_config(CFG_PATH))


# ==================================================
# SCOPE (same logic as Block 2)
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
# REGIONAL CARDS (OVERVIEW)
# ==================================================

st.markdown("## Regions")

selected_region = None
cols = st.columns(3)

for i, r in enumerate(regional_summaries):
    with cols[i % 3]:
        with st.container(border=True):
            region = r["region"]

            leaders = r["countries"]["leaders"]
            dissidents = r["countries"]["dissident"]

            st.markdown(f"### {region}")
            st.caption(
                f"{len(leaders)} leaders · "
                f"{len(dissidents)} dissidents"
            )

            st.caption(
                "Dominant posture: "
                + r.get("dominant_posture", "—")
            )

            if st.button("🔍 View region", key=f"view_{region}"):
                selected_region = region


# ==================================================
# REGION DETAILS
# ==================================================

if selected_region:
    st.divider()
    st.markdown(f"## Region details — {selected_region}")

    region = next(
        r for r in regional_summaries if r["region"] == selected_region
    )

    # -------------------------
    # Summary
    # -------------------------

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Countries", sum(
            len(v) if isinstance(v, list) else 0
            for v in region["countries"].values()
        ))

    with c2:
        st.metric("Leaders", len(region["countries"]["leaders"]))

    with c3:
        st.metric("Dissidents", len(region["countries"]["dissident"]))

    st.divider()

    # -------------------------
    # Regional concerns
    # -------------------------

    st.markdown("### Regional concerns")

    if region["regional_concerns"]:
        for t in region["regional_concerns"]:
            st.write(f"- {t}")
    else:
        st.caption("No clearly dominant regional themes.")

    st.divider()

    # -------------------------
    # Countries positioning
    # -------------------------

    st.markdown("### Countries positioning")

    col_l, col_a, col_d = st.columns(3)

    with col_l:
        st.markdown("#### Leaders")
        for c in region["countries"]["leaders"]:
            st.write(f"- {c}")

    with col_a:
        st.markdown("#### Aligned")
        for c in region["countries"]["aligned"]:
            st.write(f"- {c}")

    with col_d:
        st.markdown("#### Dissident")
        for d in region["countries"]["dissident"]:
            st.write(f"- **{d['country']}**")
            st.caption(d["deviation"]["detail"])
