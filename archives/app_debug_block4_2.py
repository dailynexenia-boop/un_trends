# -*- coding: utf-8 -*-
"""
App Debug - Block 4.2 (Argumentative Overlay)

Responsibilities:
- Load canonical entries
- Load Block4Config
- Run LLM argumentative projection (orchestrator)
- Run argumentative interpretation (core)
- Display results + trace
"""



import sys
import json
import traceback
from pathlib import Path

import streamlit as st

# --------------------------------------------------
# PATHS & IMPORTS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.config_loader import load_block4_config, Block4Config
from orchestrators.block4_2_llm import run_argument_projection
from analysis.layers.block4_2_argument_core import analyze_argument_resonance


# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="Block 4.2 - Argumentative Overlay (DEBUG)",
    layout="wide",
)

st.title("Block 4.2 — Argumentative Overlay (Debug)")
st.caption("LLM projection + analytical interpretation")


# --------------------------------------------------
# LOADERS (CACHED)
# --------------------------------------------------

@st.cache_data
def load_entries(path: Path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@st.cache_data
def load_cfg(path: Path) -> Block4Config:
    return load_block4_config(path)


CANONICAL_PATH = PROJECT_ROOT / "canonical" / "canonical.jsonl"
CFG_PATH = PROJECT_ROOT / "config" / "block4.yaml"


entries = load_entries(CANONICAL_PATH)
cfg = load_cfg(CFG_PATH)


# --------------------------------------------------
# SELECT ARGUMENT SET
# --------------------------------------------------

st.header("Argument set selection")

argument_sets = cfg.block4_2.get("argument_sets", {})

argument_set = st.selectbox(
    "Select an argument set",
    options=list(argument_sets.keys()),
)

st.write("DEBUG argument_sets keys:", list(argument_sets.keys()))
st.write("DEBUG argument_set selected:", argument_set)

st.caption(argument_sets[argument_set].get("description", ""))


# --------------------------------------------------
# RUN BLOCK 4.2
# --------------------------------------------------

st.divider()
run_btn = st.button("Run Block 4.2 — Argumentative Projection")

if run_btn:
    try:
        with st.spinner("Running LLM projection…"):
            projections = run_argument_projection(
                entries=entries,
                cfg=cfg,
                argument_set=argument_set,
            )

        st.success(f"LLM projection completed ({len(projections)} entries)")


        with st.spinner("Interpreting resonance…"):
            result = analyze_argument_resonance(
                projections=projections,
                cfg_block4_2=cfg.block4_2,
            )

        # --------------------------------------------------
        # DISPLAY RESULTS
        # --------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("High resonance arguments")
            st.write(result["arguments"]["high_resonance"])

            st.subheader("Emerging angles")
            st.write(result["arguments"]["emerging_angles"])

            st.subheader("Logical but low impact")
            st.write(result["arguments"]["logical_but_low_impact"])

        with col2:
            st.subheader("Argument counts")
            st.json(result["trace"]["counts"])

        with st.expander("Trace — entries per argument"):
            st.json(result["trace"]["entries_per_argument"])

    except Exception:
        st.error("Block 4.2 failed")
        st.code(traceback.format_exc())


# --------------------------------------------------
# DEBUG — CONFIG SNAPSHOT
# --------------------------------------------------

st.divider()
st.header("DEBUG — Block 4.2 config")

with st.expander("block4_2 (raw view)"):
    st.json(cfg.block4_2)
