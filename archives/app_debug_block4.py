# -*- coding: utf-8 -*-
"""
App Debug — Block 4.1 (CORE-ALIGNED)

Purpose:
- Explore Block 4.1 independently
- Subjects are EMERGENT (from canonical)
- No dependency on Block 4 overview
"""

import sys
import json
import traceback
from pathlib import Path
from collections import Counter

import streamlit as st

# --------------------------------------------------
# PATHS & IMPORTS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.config_loader import load_block4_config
from analysis.layers.block4_1_strategic_subject import analyze_strategic_subject


# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

st.set_page_config(page_title="Block 4.1 — Debug", layout="wide")
st.title("Block 4.1 — Strategic Core (Debug)")
st.caption("Subjects are derived from canonical content only")

# --------------------------------------------------
# LOADERS
# --------------------------------------------------

@st.cache_data
def load_canonical(path: Path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

@st.cache_data
def load_cfg(path: Path):
    return load_block4_config(path)

CANONICAL_PATH = PROJECT_ROOT / "canonical" / "canonical.jsonl"
CFG_PATH = PROJECT_ROOT / "config" / "block4.yaml"

canonical_entries = load_canonical(CANONICAL_PATH)
cfg = load_cfg(CFG_PATH)

# --------------------------------------------------
# SUBJECT DISCOVERY (EMERGENT)
# --------------------------------------------------

def extract_candidate_subjects(entries, top_n=25):
    counter = Counter()
    for e in entries:
        for kw in e.get("keywords", []):
            counter[kw.lower()] += 1
    return [kw for kw, _ in counter.most_common(top_n)]

subjects_available = extract_candidate_subjects(canonical_entries)

st.header("1️⃣ Select an emergent subject (keyword cluster)")

subject = st.selectbox(
    "Keyword / cluster derived from canonical",
    options=[""] + subjects_available,
)

# --------------------------------------------------
# ENTRY RESOLUTION
# --------------------------------------------------

def resolve_entries(entries, keyword):
    kw = keyword.lower()
    out = []
    for e in entries:
        text = (e.get("signals_text") or "").lower()
        kws = [k.lower() for k in e.get("keywords", [])]
        if kw in text or kw in kws:
            out.append(e)
    return out

# --------------------------------------------------
# RUN CORE
# --------------------------------------------------

run_btn = st.button("Run Block 4.1")

if run_btn:
    if not subject:
        st.warning("Please select a keyword.")
    else:
        try:
            with st.spinner("Running strategic core…"):
                subject_entries = resolve_entries(canonical_entries, subject)

                result = analyze_strategic_subject(
                    entries=subject_entries,
                    cfg=cfg.block4_1,   # ⬅️ IMPORTANT
                    label=subject,
                )

            st.success("Block 4.1 completed")

            # ----------------------------------
            # DISPLAY OUTPUT
            # ----------------------------------

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Perception dynamics")
                st.write(result["perception_dynamics"])

                st.subheader("Actor poles")
                st.json(result["actor_poles"])

            with col2:
                st.subheader("Recommended entry points")
                st.json(
                    result["operational_translation"]["recommended_entry_points"]
                )

                st.subheader("Missions to contact")
                st.json(
                    result["operational_translation"]["missions_to_contact"]
                )

            with st.expander("Trace"):
                st.json(result["trace"])

        except Exception:
            st.error("❌ Block 4.1 failed")
            st.code(traceback.format_exc())

# --------------------------------------------------
# DEBUG — CONFIG
# --------------------------------------------------

st.divider()
st.header("DEBUG — Block 4.1 config")

with st.expander("block4_1 (raw)"):
    st.json(cfg.block4_1)
