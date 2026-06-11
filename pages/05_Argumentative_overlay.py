# -*- coding: utf-8 -*-
"""
Block 4.2 — Argumentative Landscape (FINAL)

Pipeline:
1. Explicit LLM argumentative projection (voluntary, traceable)
2. Deterministic resonance analysis (core)
3. Argument-centric UI with full entry-level trace

NO hidden logic.
NO YAML-driven semantics.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter

import streamlit as st



# ==================================================
# PATHS & IMPORTS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from shared.bootstrap import PROJECT_ROOT
from analysis.config_loader import load_block4_config
from analysis.layers.block4_2_argument_core import analyze_argument_resonance
from orchestrators.block4_2_llm import run_argument_projection


# ==================================================
# PAGE SETUP
# ==================================================

st.set_page_config(page_title="Argumentative Landscape", layout="wide")
st.title("Argumentative landscape")
st.caption("Normative and legal arguments across the session (LLM-projected, traceable)")


# ==================================================
# LOADERS
# ==================================================

@st.cache_data
def load_canonical(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

@st.cache_data
def load_cfg(path: Path):
    return load_block4_config(path)


entries = load_canonical(PROJECT_ROOT / "canonical" / "canonical.jsonl")
cfg = load_cfg(PROJECT_ROOT / "config" / "block4.yaml")


# ==================================================
# UI STATE
# ==================================================

if "active_argument" not in st.session_state:
    st.session_state.active_argument = None

if "last_projection" not in st.session_state:
    st.session_state.last_projection = None


# ==================================================
# SCOPE
# ==================================================

st.header("Scope")

confs = sorted({e.get("conference") for e in entries if isinstance(e.get("conference"), str)})
conference = st.selectbox("Conference", confs)

scoped_entries = [
    e for e in entries
    if e.get("conference") == conference
]

st.caption(f"{len(scoped_entries)} entries in scope")

def sanitize_argument_sets(argument_sets: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Ensures argument_sets is a dict of dicts.
    Accepts shorthand string configs.
    """
    fixed = {}

    for name, data in argument_sets.items():
        if isinstance(data, dict):
            fixed[name] = data
        elif isinstance(data, str):
            fixed[name] = {
                "description": "",
            }

    return fixed


# ==================================================
# ARGUMENT SET SELECTION
# ==================================================

st.subheader("Argument set")

block4_2_cfg = cfg.get("block4_2", {})
argument_sets_raw = block4_2_cfg.get("argument_sets", {})
argument_sets = sanitize_argument_sets(argument_sets_raw)

if not argument_sets:
    st.error("No argument sets defined in block4_2 config.")
    st.stop()

argument_set = st.selectbox(
    "Select an argument set",
    options=list(argument_sets.keys()),
)

if argument_sets[argument_set].get("description"):
    st.caption(argument_sets[argument_set]["description"])


# ==================================================
# RUN LLM PROJECTION (EXPLICIT)
# ==================================================

run_btn = st.button("Run argumentative projection")

if not run_btn and not st.session_state.last_projection:
    st.info("Run the argumentative projection to generate arguments.")
    st.stop()

cache_key = (conference, argument_set)

# --- session_state migration ---
if (
    "last_projection" in st.session_state
    and isinstance(st.session_state.last_projection, list)
):
    st.session_state.last_projection = None

cache_key = (conference, argument_set)

if run_btn:
    with st.spinner("Running LLM argumentative projection…"):
        projections = run_argument_projection(
            entries=scoped_entries,
            cfg=cfg,
            argument_set=argument_set,
        )

    st.session_state.last_projection = {
        "key": cache_key,
        "data": projections,
    }
    st.success(f"Argumentative projection completed ({len(projections)} entries)")

elif (
    st.session_state.last_projection
    and st.session_state.last_projection.get("key") == cache_key
):
    projections = st.session_state.last_projection["data"]

else:
    st.info("Run the argumentative projection for the current scope.")
    st.stop()

# ==================================================
# CORE 4.2 — RESONANCE ANALYSIS
# ==================================================

result = analyze_argument_resonance(
    projections=projections,
    cfg_block4_2=block4_2_cfg,
)


# ==================================================
# GLOBAL METRICS
# ==================================================

st.subheader("Argumentative overview")

c1, c2, c3 = st.columns(3)
c1.metric("Entries analysed", result["trace"]["total_entries"])
c2.metric("Distinct arguments", len(result["trace"]["counts"]))
c3.metric("Total mentions", sum(result["trace"]["counts"].values()))


# ==================================================
# ARGUMENT INDEX — 3 COLUMNS
# ==================================================

st.subheader("Argument index")

col_high, col_emerg, col_low = st.columns(3)

# ---------- HIGH RESONANCE ----------
with col_high:
    st.markdown("### 🔴 High resonance")
    for arg in result["arguments"]["high_resonance"]:
        hits = result["trace"]["counts"].get(arg, 0)
        if st.button(f"{arg} ({hits})", key=f"high_{arg}"):
            st.session_state.active_argument = arg

# ---------- EMERGING ----------
with col_emerg:
    st.markdown("### 🟡 Emerging")
    for arg in result["arguments"]["emerging_angles"]:
        hits = result["trace"]["counts"].get(arg, 0)
        if st.button(f"{arg} ({hits})", key=f"emerg_{arg}"):
            st.session_state.active_argument = arg

# ---------- LOW IMPACT ----------
with col_low:
    st.markdown("### ⚪ Logical but low impact")
    for arg in result["arguments"]["logical_but_low_impact"]:
        hits = result["trace"]["counts"].get(arg, 0)
        if st.button(f"{arg} ({hits})", key=f"low_{arg}"):
            st.session_state.active_argument = arg


# ==================================================
# ARGUMENT DETAIL VIEW (TRACE-CENTRIC)
# ==================================================

if st.session_state.active_argument:

    arg = st.session_state.active_argument
    st.divider()
    st.header(f"Argument — {arg}")

    hits = result["trace"]["counts"].get(arg, 0)
    st.caption(f"Mentions across session: {hits}")

    entry_ids = result["trace"]["entries_per_argument"].get(arg, [])

    st.subheader("Source entries")

    entry_index = {e.get("entry_id"): e for e in scoped_entries}

    for eid in entry_ids[:12]:  # guard rail
        e = entry_index.get(eid)
        if not e:
            continue

        with st.container(border=True):

            country = (
                e.get("speaker_structure", {})
                 .get("primary_speaker", {})
                 .get("name", "—")
            )

            st.markdown(f"**{country}** · {e.get('date', '—')} · `{eid}`")

            txt = (e.get("signals_text") or "").strip()
            if txt:
                st.markdown(f"> {txt[:400]}")

            kws = e.get("keywords") or []
            if kws:
                st.caption("Keywords: " + ", ".join(kws))

    # ---------- CONTEXTUAL READINGS ----------
    st.subheader("Countries mobilising this argument")

    countries = Counter(
        entry_index[eid]
        .get("speaker_structure", {})
        .get("primary_speaker", {})
        .get("name")
        for eid in entry_ids
        if eid in entry_index
    )

    for c, n in countries.most_common(10):
        st.write(f"- {c} ({n})")

    if st.button("Clear argument selection"):
        st.session_state.active_argument = None
