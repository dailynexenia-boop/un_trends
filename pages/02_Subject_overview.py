# -*- coding: utf-8 -*-
"""
Block 4 — Strategic Cartography
Block 4.1 — Strategic Subject (Sidebar Mode)

FINAL INTEGRATED VERSION
"""

import sys
import json
from pathlib import Path
from typing import Any, Dict, List
import datetime as dt
from collections import Counter, defaultdict
from shared.bootstrap import PROJECT_ROOT

import streamlit as st

# ==================================================
# PATHS & IMPORTS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.config_loader import load_block4_config
from analysis.layers.block4_session_overview import analyze_session_overview
from analysis.layers.block4_1_strategic_subject import analyze_strategic_subject


# ==================================================
# PAGE SETUP
# ==================================================

st.set_page_config(page_title="Strategic Analysis", layout="wide")
st.title("Strategic Analysis")
st.caption("Session cartography and strategic subject analysis)")

# ==================================================
# RESPONSIVE GRID CSS
# ==================================================

st.markdown(
    """
    <style>
    .subject-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }
    .subject-card {
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 10px;
        padding: 1rem;
        background: rgba(255,255,255,0.03);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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

if "mode" not in st.session_state:
    st.session_state.mode = "overview"   # overview | strategic

if "active_strategic_subject" not in st.session_state:
    st.session_state.active_strategic_subject = None


# ==================================================
# CONFIG SANITIZERS (BLOCK 4)
# ==================================================

def sanitize_keyword_aggregations(cfg_overview: Dict[str, Any]) -> Dict[str, Any]:
    ka = cfg_overview.get("keyword_aggregations")
    if not isinstance(ka, dict):
        cfg_overview["keyword_aggregations"] = {}
        return cfg_overview

    fixed = {}
    for sid, data in ka.items():
        if isinstance(data, dict):
            fixed[sid] = {
                "label": data.get("label", sid),
                "members": data.get("members", []),
            }
        elif isinstance(data, str):
            fixed[sid] = {"label": data, "members": [sid]}
        elif isinstance(data, list):
            fixed[sid] = {"label": sid, "members": data}

    cfg_overview["keyword_aggregations"] = fixed
    return cfg_overview


def sanitize_limits(cfg_overview: Dict[str, Any]) -> Dict[str, Any]:
    defaults = {"top_subjects": 30, "top_countries": 6, "top_angles": 10}
    limits = cfg_overview.get("limits")

    if not isinstance(limits, dict):
        cfg_overview["limits"] = defaults
        return cfg_overview

    fixed = {}
    for k, d in defaults.items():
        try:
            fixed[k] = int(limits.get(k))
        except Exception:
            fixed[k] = d

    cfg_overview["limits"] = fixed
    return cfg_overview


# ==================================================
# HELPERS (UI ONLY)
# ==================================================

def norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def entry_country(e):
    return (
        e.get("speaker_structure", {})
         .get("primary_speaker", {})
         .get("name")
    )


def build_subject_subset(entries, subject_label, cfg_overview):
    keyword_to_subjects = defaultdict(set)
    subject_labels = {}

    for sid, data in cfg_overview.get("keyword_aggregations", {}).items():
        label = data.get("label", sid)
        subject_labels[sid] = label
        for k in data.get("members", []):
            keyword_to_subjects[norm(k)].add(sid)

    label_to_sid = {v: k for k, v in subject_labels.items()}
    target_sid = label_to_sid.get(subject_label, subject_label)

    subset = []
    for e in entries:
        kws = [norm(k) for k in e.get("keywords", []) if isinstance(k, str)]
        touched = set()
        for k in kws:
            if k in keyword_to_subjects:
                touched.update(keyword_to_subjects[k])
            else:
                touched.add(k)
        if target_sid in touched:
            subset.append(e)
    return subset


def micro_distributions(entries):
    dist = defaultdict(Counter)
    for e in entries:
        micro = e.get("micro_analysis") or {}
        if not isinstance(micro, dict):
            continue
        for k, v in micro.items():
            if isinstance(v, (str, bool, int)):
                dist[k][str(v)] += 1
    return dist


def sample_citations(entries, n=6, max_chars=420):
    out = []
    for e in entries:
        txt = (e.get("signals_text") or "").strip()
        if not txt:
            continue
        out.append({
            "entry_id": e.get("entry_id"),
            "date": e.get("date"),
            "country": entry_country(e),
            "text": txt[:max_chars],
        })
        if len(out) >= n:
            break
    return out

def render_entry_trace(entries, max_items=12, max_chars=400):
    """
    UI-only trace renderer for Block 4.1
    Shows entry_id, country, date, signals_text excerpt, and keywords.
    """
    st.subheader("Trace — source entries")

    if not entries:
        st.caption("No source entries available for this strategic subject.")
        return

    for e in entries[:max_items]:
        with st.container(border=True):

            header_parts = []
            if e.get("country"):
                header_parts.append(e["country"])
            if e.get("date"):
                header_parts.append(str(e["date"]))
            if e.get("entry_id"):
                header_parts.append(f"`{e['entry_id']}`")

            st.markdown(" · ".join(header_parts))

            txt = (e.get("signals_text") or "").strip()
            if txt:
                st.markdown(f"> {txt[:max_chars]}")

            kws = e.get("keywords") or []
            if kws:
                st.caption("Keywords: " + ", ".join(kws))


# ==================================================
# SIDEBAR — BLOCK 4.1 (STRATEGIC SUBJECT)
# ==================================================

with st.sidebar:
    st.header("Strategic subject")
    st.caption("Deep strategic analysis (config-defined subjects only)")

    cfg_41 = cfg.get("block4_1", {})
    subjects_cfg = cfg_41.get("subjects", {})

    if subjects_cfg:
        subject_ids = list(subjects_cfg.keys())

        sid = st.selectbox(
            "Select strategic subject",
            ["—"] + subject_ids,
            format_func=lambda x: "—" if x == "—" else subjects_cfg[x].get("label", x),
        )

        if sid != "—":
            if st.button("Enter strategic analysis"):
                st.session_state.mode = "strategic"
                st.session_state.active_strategic_subject = sid

        if st.session_state.mode == "strategic":
            if st.button("Exit strategic analysis"):
                st.session_state.mode = "overview"
                st.session_state.active_strategic_subject = None
    else:
        st.info("No strategic subjects defined in config.")


# ==================================================
# SCOPE (COMMON)
# ==================================================

st.header("Scope")

confs = sorted({e.get("conference") for e in entries if isinstance(e.get("conference"), str)})
conference = st.selectbox("Conference", confs)

scoped = [e for e in entries if e.get("conference") == conference]

dates = sorted({e.get("date") for e in scoped if isinstance(e.get("date"), str)})
date_mode = st.radio("Date filter", ["All dates", "Single day", "Date range"], horizontal=True)

start_date = end_date = None
if date_mode == "Single day" and dates:
    start_date = end_date = st.date_input("Select day", dt.date.fromisoformat(dates[0]))
elif date_mode == "Date range" and dates:
    start_date, end_date = st.date_input(
        "Select range",
        [dt.date.fromisoformat(dates[0]), dt.date.fromisoformat(dates[-1])]
    )

def in_scope(e):
    if e.get("conference") != conference:
        return False
    if not start_date:
        return True
    try:
        d = dt.date.fromisoformat(e.get("date"))
    except Exception:
        return False
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True

scoped_entries = [e for e in entries if in_scope(e)]
st.caption(f"{len(scoped_entries)} entries selected")


# ==================================================
# MAIN RENDERING
# ==================================================

if st.session_state.mode == "overview":

    # ---------- BLOCK 4 ----------

    cfg_overview = cfg.get("block4", {})
    cfg_overview = sanitize_keyword_aggregations(cfg_overview)
    cfg_overview = sanitize_limits(cfg_overview)

    overview = analyze_session_overview(scoped_entries, cfg_overview)
    if not overview:
        st.warning("No subjects detected.")
        st.stop()

    st.subheader("Session overview")

    countries = {entry_country(e) for e in scoped_entries if entry_country(e)}
    c1, c2, c3 = st.columns(3)
    c1.metric("Subjects", len(overview))
    c2.metric("Entries", len(scoped_entries))
    c3.metric("Countries", len(countries))

    st.subheader("Subject selection")

    all_subjects = [s["subject"] for s in overview]
    selected = st.multiselect(
        "Search and select subjects (leave empty to show main ones)",
        options=all_subjects,
        default=[]
    )

    if not selected:
        filtered = sorted(
            overview,
            key=lambda x: (x["entries"], x["countries_total"]),
            reverse=True
        )
    else:
        filtered = [s for s in overview if s["subject"] in selected]

    st.markdown('<div class="subject-grid">', unsafe_allow_html=True)

    for s in filtered:
        st.markdown('<div class="subject-card">', unsafe_allow_html=True)

        st.markdown(f"### {s['subject']}")
        st.caption(f"{s['entries']} entries · {s['countries_total']} countries")

        if s["top_countries"]:
            st.write("**Top countries**:", ", ".join(s["top_countries"][:6]))

        if s["angles"]:
            st.write("**Key angles**:", ", ".join(s["angles"][:8]))

        with st.expander("Analytical drilldown (Block 4 depth)"):
            subset = build_subject_subset(scoped_entries, s["subject"], cfg_overview)
            st.caption(f"{len(subset)} entries in subset")

            dist = micro_distributions(subset)
            for k, counter in dist.items():
                st.write(
                    f"**{k}**: "
                    + ", ".join(f"{v} ({n})" for v, n in counter.most_common(6))
                )

            for c in sample_citations(subset):
                st.markdown(
                    f"> *{c['text']}*\n\n"
                    f"— **{c['country']}**, {c['date']} · `{c['entry_id']}`"
                )

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

else:

    # ---------- BLOCK 4.1 ----------

    sid = st.session_state.active_strategic_subject
    cfg_41 = cfg.get("block4_1", {})
    subject_cfg = cfg_41["subjects"][sid]

    st.header(f"Strategic subject — {subject_cfg.get('label', sid)}")
    st.caption(subject_cfg.get("description", ""))

    members = subject_cfg.get("members", [])
    member_norm = {norm(m) for m in members}

    subset = [
        e for e in scoped_entries
        if member_norm & {norm(k) for k in e.get("keywords", []) if isinstance(k, str)}
    ]

    st.caption(f"{len(subset)} entries in scope")

    adapted = [{
        **e,
        "country": entry_country(e),
        "signals_text": e.get("signals_text", ""),
        "keywords": e.get("keywords", []),
    } for e in subset]

    result = analyze_strategic_subject(
        entries=adapted,
        cfg=cfg_41,
        label=subject_cfg.get("label", sid),
    )

    st.subheader("Perception dynamics")
    for p in result["perception_dynamics"]:
        st.write(f"- {p}")

    st.subheader("Actor poles")
    for pole, countries in result["actor_poles"].items():
        st.write(f"**{pole.title()}**: {', '.join(countries)}")

    st.subheader("Recommended entry points")
    for ep in result["operational_translation"]["recommended_entry_points"]:
        st.write(
            f"- **{ep['label']}** (score: {ep['score']}) · "
            f"{', '.join(ep.get('supporting_terms', []))}"
        )

    st.subheader("Missions to contact")
    st.write(", ".join(result["operational_translation"]["missions_to_contact"]))

    st.caption(
        f"Trace — {result['trace']['entries_used']} entries · "
        f"{result['trace']['countries_involved']} countries"

    )

    render_entry_trace(adapted, max_items=12)
