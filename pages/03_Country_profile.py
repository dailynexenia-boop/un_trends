# -*- coding: utf-8 -*-
"""
Block 2 — Country Profiles (FINAL, FIXED ORDER)

ORDER (NON-NEGOTIABLE):
1. Header
2. Scope
3. Filters + Search
4. Country detail (if selected)
5. Country cards grid
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.layers.block2_country_profiles_core import analyze_country_profiles
from analysis.layers.block2_5_contextual_signals_core import analyze_contextual_signals
from analysis.config_loader import load_block4_config
from shared.bootstrap import PROJECT_ROOT

# ==================================================
# PATHS
# ==================================================

CANONICAL_PATH = PROJECT_ROOT / "canonical" / "canonical.jsonl"
CFG_PATH = PROJECT_ROOT / "config" / "block4.yaml"

# ==================================================
# SESSION STATE
# ==================================================

st.session_state.setdefault("selected_country", None)

# ==================================================
# HELPERS
# ==================================================

def participation_level(n: int) -> str:
    if n <= 2:
        return "low"
    if n <= 5:
        return "medium"
    return "high"


def safe_country(e: dict) -> str | None:
    return e.get("primary_speaker") or e.get("speaker_raw")


def entry_watch_flag(e: dict) -> bool:
    return bool((e.get("micro_analysis") or {}).get("watch_flag"))


def extract_diplomatic_acts(e: dict) -> list[str]:
    acts = ((e.get("micro_analysis") or {}).get("diplomatic_acts") or {})
    return [k for k, v in acts.items() if v]


def explain_watch_flag(e: dict) -> str | None:
    micro = e.get("micro_analysis") or {}
    reasons = []
    if micro.get("risk_level") == "high":
        reasons.append("High political risk")
    if micro.get("explicitness_level") in ("high", "very_high"):
        reasons.append("High explicitness level")
    if extract_diplomatic_acts(e):
        reasons.append("Presence of diplomatic acts")
    return "; ".join(reasons) if reasons else None


def normalize_block2_cfg(cfg):
    """
    Normalize Block2 thresholds regardless of cfg/block2 structure.
    Supports:
    - cfg as Block4Config (object)
    - cfg.block2 as object OR dict
    - thresholds stored as dict OR stringified dict
    """
    block2 = getattr(cfg, "block2", None)
    if block2 is None:
        return cfg

    if isinstance(block2, dict):
        thresholds = block2.get("thresholds", {}) or {}
    else:
        thresholds = getattr(block2, "thresholds", {}) or {}

    for key in ["volatility", "risk_tolerance", "diversity"]:
        val = thresholds.get(key)
        if isinstance(val, str):
            thresholds[key] = ast.literal_eval(val)

    if isinstance(block2, dict):
        block2["thresholds"] = thresholds
    else:
        block2.thresholds = thresholds

    return cfg


def contextual_badge_count(ctx_by_country: dict, country: str) -> int:
    return sum(1 for r in ctx_by_country.get(country, []) if r.get("contextual_signal"))


# ==================================================
# LOADERS
# ==================================================

@st.cache_data
def load_canonical(path: Path):
    entries = []
    by_conf = defaultdict(list)
    dates = defaultdict(set)

    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)

            conf = e.get("conference")
            if not conf:
                continue

            entries.append(e)
            by_conf[conf].append(e)

            if e.get("date"):
                dates[conf].add(e["date"])

    return entries, by_conf, {c: sorted(d) for c, d in dates.items()}


@st.cache_data
def compute_contextual_signals(_entries, _profiles_by_country, _cfg):
    """
    Block 2.5 computation cached for current scope.
    Returns: dict[country] -> list[result rows]
    """
    cfg_block2_5 = getattr(_cfg, "block2_5", {})
    out = analyze_contextual_signals(
        entries=_entries,
        profiles_by_country=_profiles_by_country,
        cfg_block2_5=cfg_block2_5,
        debug=False,
        include_entry_debug=False,
    )

    by_country = defaultdict(list)
    for r in out.get("results", []):
        c = r.get("country")
        if c:
            by_country[c].append(r)

    return dict(by_country)

# ==================================================
# PAGE HEADER
# ==================================================

st.set_page_config("Country Profiles", layout="wide")
st.title("Country Profiles")
st.caption("Scan → filter → focus → explain · no JSON")

if not CANONICAL_PATH.exists():
    st.error("canonical.jsonl not found")
    st.stop()

entries, entries_by_conf, dates_by_conf = load_canonical(CANONICAL_PATH)
cfg = normalize_block2_cfg(load_block4_config(CFG_PATH))

# ==================================================
# SCOPE
# ==================================================

st.markdown("## Scope")

conf = st.selectbox("Conference", sorted(entries_by_conf))
available_dates = dates_by_conf.get(conf, [])

time_mode = st.radio(
    "Date filter",
    ["All dates", "Single day", "Date range"],
    horizontal=True,
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
# INDEX + COMPUTE (BLOCK 2)
# ==================================================

entries_by_country = defaultdict(list)
for e in filtered_entries:
    c = safe_country(e)
    if c:
        entries_by_country[c].append(e)

profiles = analyze_country_profiles(filtered_entries, cfg)
profiles_by_country = {p["country"]: p for p in profiles}

# ==================================================
# BLOCK 2.5 (CONTEXTUAL) — COMPUTE ONCE
# ==================================================

ctx_by_country = compute_contextual_signals(filtered_entries, profiles_by_country, cfg)

# ==================================================
# DIPLOMATIC ACTS IN SCOPE (BEFORE FILTER UI)
# ==================================================

all_diplomatic_acts = sorted({
    act
    for entries_list in entries_by_country.values()
    for e in entries_list
    for act in extract_diplomatic_acts(e)
})

# ==================================================
# FILTERS + SEARCH (BEFORE visible_profiles)
# ==================================================

st.markdown("## Filters")

c1, c2, c3, c4 = st.columns(4)

with c1:
    posture_filter = st.multiselect(
        "Speaking style",
        ["passive", "procedural", "cooperative", "normative", "assertive"],
    )

with c2:
    risk_filter = st.multiselect(
        "Risk tolerance",
        ["low", "medium", "high"],
    )

with c3:
    participation_filter = st.multiselect(
        "Participation",
        ["low", "medium", "high"],
    )

with c4:
    diplomatic_act_filter = st.multiselect(
        "Diplomatic acts",
        all_diplomatic_acts,
    )

st.markdown("## Search country")
search = st.text_input(
    "Type a country name",
    placeholder="e.g. Algeria, France, Ukraine",
).strip().lower()

# ==================================================
# VISIBLE PROFILES (APPLY FILTERS + SEARCH)
# ==================================================

visible_profiles = {}

for country, profile in profiles_by_country.items():
    # Search
    if search and search not in country.lower():
        continue

    # Posture
    if posture_filter and profile["posture"]["dominant"] not in posture_filter:
        continue

    # Risk
    if risk_filter and profile["risk_profile"]["risk_tolerance"] not in risk_filter:
        continue

    # Participation
    if participation_filter:
        lvl = participation_level(profile["activity"]["interventions_count"])
        if lvl not in participation_filter:
            continue

    # Diplomatic acts filter
    if diplomatic_act_filter:
        entries_c = entries_by_country.get(country, [])
        has_act = any(
            any(act in diplomatic_act_filter for act in extract_diplomatic_acts(e))
            for e in entries_c
        )
        if not has_act:
            continue

    visible_profiles[country] = profile

# Auto-focus if single result
if search and len(visible_profiles) == 1:
    st.session_state.selected_country = next(iter(visible_profiles.keys()))

# Reset selection if filtered out
if st.session_state.selected_country and st.session_state.selected_country not in visible_profiles:
    st.session_state.selected_country = None

# ==================================================
# COUNTRY DETAIL (AFTER FILTERS/SEARCH, BEFORE CARDS)
# ==================================================

country = st.session_state.selected_country

if country:
    profile = profiles_by_country.get(country)
    country_entries = entries_by_country.get(country, [])

    if profile:
        st.divider()
        st.markdown(f"## {country}")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Participation", participation_level(profile["activity"]["interventions_count"]))
        with m2:
            st.metric("Speaking style", profile["posture"]["dominant"])
        with m3:
            st.metric("Political risk", profile["risk_profile"]["risk_tolerance"])

        watch_n = sum(entry_watch_flag(e) for e in country_entries)
        if watch_n:
            with st.container(border=True):
                st.markdown(f"👁️ **{watch_n} intervention(s) flagged for watch in this scope**")

        # Topics (country)
        st.divider()
        st.markdown("### Main themes")
        topics = sorted(
            (profile.get("topics", {}).get("central", {}) or {}).items(),
            key=lambda x: x[1],
            reverse=True,
        )
        if topics:
            for t, n in topics[:5]:
                st.write(f"- **{t}** ({n} mentions)")
        else:
            st.caption("No dominant themes in this scope.")

        # Contextual signals (Block 2.5) — INSIDE the country block (fix)
        st.divider()
        st.markdown("### Contextual signals")

        rows = [r for r in ctx_by_country.get(country, []) if r.get("contextual_signal")]

        if not rows:
            st.caption("No contextual deviation detected for this country in the current scope.")
        else:
            st.caption(f"{len(rows)} intervention(s) deviate from the country baseline in this scope.")

            for r in rows:
                eid = r.get("entry_id")
                title = f"Entry {eid}" if eid else "Intervention"

                with st.expander(title):
                    rationale = r.get("rationale") or []
                    if rationale:
                        st.markdown("**Why this intervention deviates from baseline**")
                        for line in rationale:
                            st.info(line)

                    sigs = r.get("contextual_signals") or {}
                    if sigs:
                        high = any(v == "high" for v in sigs.values())
                        level = "high" if high else "moderate"
                        st.caption(f"Deviation level: {level}")

        # Diplomatic acts summary (country)
        st.divider()
        st.markdown("### Diplomatic acts (scope summary)")

        acts_counter = defaultdict(int)
        for e in country_entries:
            for act in extract_diplomatic_acts(e):
                acts_counter[act] += 1

        if not acts_counter:
            st.caption("No explicit diplomatic acts detected in this scope.")
        else:
            for act, n in sorted(acts_counter.items(), key=lambda x: x[1], reverse=True):
                st.write(f"- **{act}** ({n})")

        # Interventions (old readable block)
        st.divider()
        with st.expander("📄 View all interventions"):
            for e in sorted(country_entries, key=lambda x: x.get("date") or ""):
                st.markdown(f"**{e.get('date')} — {e.get('conference')}**")

                if entry_watch_flag(e):
                    st.markdown("👁️ **Watch flag raised**")
                    reason = explain_watch_flag(e)
                    if reason:
                        st.caption(f"Reason: {reason}")

                topics_i = ((e.get("micro_analysis") or {}).get("topics_analysis") or {})
                if topics_i.get("central_topics"):
                    st.caption("Central topics: " + ", ".join(topics_i["central_topics"]))
                if topics_i.get("secondary_topics"):
                    st.caption("Secondary topics: " + ", ".join(topics_i["secondary_topics"]))

                acts = extract_diplomatic_acts(e)
                if acts:
                    st.caption("Diplomatic acts: " + ", ".join(acts))

                if e.get("signals_text"):
                    st.markdown(f"> {e['signals_text']}")

                if e.get("entry_id"):
                    st.caption(f"`entry_id: {e['entry_id']}`")

                st.markdown("---")

# ==================================================
# COUNTRY CARDS GRID (SCAN)
# ==================================================

st.divider()
st.markdown("## Countries")

if not visible_profiles:
    st.warning("No country matches the current filters.")
    st.stop()

cols = st.columns(3)

for i, (c, p) in enumerate(sorted(visible_profiles.items())):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"### {c}")

            ctx_n = contextual_badge_count(ctx_by_country, c)
            badge = f" ⚠ {ctx_n}" if ctx_n else ""

            st.markdown(
                f"**{p['activity']['interventions_count']} statements**{badge}  \n"
                f"{p['posture']['dominant']} · {p['risk_profile']['risk_tolerance']}"
            )

            top_topics = sorted(
                (p.get("topics", {}).get("central", {}) or {}).items(),
                key=lambda x: x[1],
                reverse=True,
            )
            if top_topics:
                st.caption(f"Main theme: **{top_topics[0][0]}**")

            if st.button("🔍 View details", key=f"view_{c}"):
                st.session_state.selected_country = c
