# -*- coding: utf-8 -*-
"""
Block 2 — Country Profiles (UI) + Block 2.5 overlay

Stable mixed UX:
- Global cards view (never blank)
- Filters + search (non-destructive)
- Persistent country details (session_state)
- Intern-friendly language
- Block 2.5 as contextual right panel (no duplication)
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

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.layers.block2_country_profiles_core import analyze_country_profiles
from analysis.config_loader import load_block4_config
from analysis.layers.block2_5_contextual_signals_core import analyze_contextual_signals


# ==================================================
# PATHS
# ==================================================

CANONICAL_PATH = PROJECT_ROOT / "canonical" / "canonical.jsonl"
CFG_PATH = PROJECT_ROOT / "config" / "block4.yaml"


# ==================================================
# SESSION STATE INIT (CRITICAL)
# ==================================================

if "selected_country" not in st.session_state:
    st.session_state.selected_country = None

if "show_contextual" not in st.session_state:
    st.session_state.show_contextual = False


# ==================================================
# CONFIG ADAPTERS (DO NOT TOUCH YAML)
# ==================================================

def normalize_block2_cfg(cfg):
    thresholds = cfg.block2.get("thresholds", {})
    for k in ["volatility", "risk_tolerance", "diversity"]:
        if isinstance(thresholds.get(k), str):
            thresholds[k] = ast.literal_eval(thresholds[k])
    return cfg


def normalize_block2_5_cfg(cfg_block2_5: dict) -> dict:
    """
    Safe defaults if block2_5 is missing or incomplete in YAML.
    """
    if not isinstance(cfg_block2_5, dict):
        cfg_block2_5 = {}

    cfg_block2_5.setdefault("posture_order", ["procedural", "passive", "cooperative", "assertive"])
    cfg_block2_5.setdefault("thresholds", {})
    cfg_block2_5["thresholds"].setdefault("contextual_signal", {"min_high": 1, "min_total": 2})
    cfg_block2_5.setdefault("rules", {})
    cfg_block2_5["rules"].setdefault("ignore_speakers", ["unknown"])

    return cfg_block2_5


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


@st.cache_data
def compute_block2_5(_filtered_entries, _profiles_by_country, _cfg_block2_5):
    """
    Cached contextual signals computation for current scope.
    Returns:
      - by_country: dict[country] -> list[result rows]
      - by_entry: dict[entry_id] -> result row
      - dbg: debug dict
    """
    out = analyze_contextual_signals(
        entries=_filtered_entries,
        profiles_by_country=_profiles_by_country,
        cfg_block2_5=_cfg_block2_5,
        debug=True,
        include_entry_debug=False
    )

    by_country = defaultdict(list)
    by_entry = {}

    for r in out.get("results", []):
        c = r.get("country")
        eid = str(r.get("entry_id"))
        if c:
            by_country[c].append(r)
        if eid:
            by_entry[eid] = r

    return dict(by_country), by_entry, out.get("debug", {})


# ==================================================
# PAGE
# ==================================================

st.set_page_config("Country Profiles", layout="wide")
st.title("Country Profiles")
st.caption("Overview and detailed exploration of country interventions")

if not CANONICAL_PATH.exists():
    st.error("canonical.jsonl not found")
    st.stop()

entries, entries_by_conf, dates_by_conf = load_canonical(CANONICAL_PATH)
cfg = normalize_block2_cfg(load_block4_config(CFG_PATH))

# block2_5 namespace (safe defaults)
cfg_block2_5 = normalize_block2_5_cfg(cfg.get("block2_5", {}))


# ==================================================
# SCOPE (CONFERENCE + DATE)
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
# INDEX BY COUNTRY (for drill-down text)
# ==================================================

entries_by_country = defaultdict(list)

for e in filtered_entries:
    # keep same behavior as your UI
    country = e.get("primary_speaker") or e.get("speaker_raw")
    if country:
        entries_by_country[country].append(e)


# ==================================================
# CORE COMPUTATION (BLOCK 2)
# ==================================================

profiles = analyze_country_profiles(filtered_entries, cfg)
profiles_by_country = {p["country"]: p for p in profiles}


# ==================================================
# BLOCK 2.5 COMPUTATION (CACHED)
# ==================================================

block2_5_by_country, block2_5_by_entry, block2_5_dbg = compute_block2_5(
    filtered_entries, profiles_by_country, cfg_block2_5
)


# ==================================================
# FILTERS
# ==================================================

st.markdown("## Filters")

c1, c2, c3 = st.columns(3)

with c1:
    posture_filter = st.multiselect(
        "Speaking style",
        ["passive", "procedural", "cooperative", "normative", "assertive"]
    )

with c2:
    risk_filter = st.multiselect(
        "Risk tolerance",
        ["low", "medium", "high"]
    )

with c3:
    participation_filter = st.multiselect(
        "Participation level",
        ["low", "medium", "high"]
    )


def participation_level(n):
    if n <= 2:
        return "low"
    if n <= 5:
        return "medium"
    return "high"


def profile_matches(p):
    if posture_filter and p["posture"]["dominant"] not in posture_filter:
        return False
    if risk_filter and p["risk_profile"]["risk_tolerance"] not in risk_filter:
        return False
    if participation_filter:
        lvl = participation_level(p["activity"]["interventions_count"])
        if lvl not in participation_filter:
            return False
    return True


# ==================================================
# SEARCH (MUST BE DEFINED BEFORE FILTERING)
# ==================================================

st.markdown("## Search country")

search_query = st.text_input(
    "Type a country name",
    placeholder="e.g. France, Algeria, Ukraine"
).strip().lower()


# ==================================================
# VISIBLE PROFILES (FILTERS + SEARCH)
# ==================================================

visible_profiles = {
    c: p for c, p in profiles_by_country.items()
    if profile_matches(p) and (not search_query or search_query in c.lower())
}

# Reset selection if no longer visible
if (
    st.session_state.selected_country
    and st.session_state.selected_country not in visible_profiles
):
    st.session_state.selected_country = None


# ==================================================
# COUNTRY CARDS (OVERVIEW)
# ==================================================

st.markdown("## Countries")

if not visible_profiles:
    st.warning("No country matches the current filters.")
    st.stop()

STYLE_BADGE = {
    "passive": "⚪ Passive",
    "procedural": "⚪ Procedural",
    "cooperative": "🟢 Cooperative",
    "normative": "🔵 Normative",
    "assertive": "🔴 Assertive",
}

RISK_BADGE = {
    "low": "🟢 Low risk",
    "medium": "🟠 Medium risk",
    "high": "🔴 High risk",
}

def contextual_count(country: str) -> int:
    rows = block2_5_by_country.get(country, [])
    return sum(1 for r in rows if r.get("contextual_signal"))

cols = st.columns(3)

for i, (country, p) in enumerate(sorted(visible_profiles.items())):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"### {country}")

            count = p["activity"]["interventions_count"]
            style = p["posture"]["dominant"]
            risk = p["risk_profile"]["risk_tolerance"]

            ctx_n = contextual_count(country)
            ctx_badge = f" ⚠ {ctx_n}" if ctx_n else ""

            st.markdown(
                f"**{count} statements**{ctx_badge}  \n"
                f"{STYLE_BADGE.get(style, style)} · {RISK_BADGE.get(risk, risk)}"
            )

            top_topics = sorted(
                p["topics"]["central"].items(),
                key=lambda x: x[1],
                reverse=True
            )

            if top_topics:
                st.caption(f"Main theme: **{top_topics[0][0]}**")

            if st.button("🔍 View details", key=f"view_{country}"):
                st.session_state.selected_country = country


# ==================================================
# COUNTRY DETAILS (DRILL-DOWN) + BLOCK 2.5 PANEL
# ==================================================

selected_country = st.session_state.selected_country

if selected_country:
    st.divider()
    st.markdown("## Country details")

    profile = visible_profiles[selected_country]
    country_entries = entries_by_country.get(selected_country, [])

    POSTURE_EXPLAIN = {
        "passive": "Mostly neutral or minimal statements",
        "procedural": "Focuses on process and formal rules",
        "cooperative": "Emphasizes cooperation and consensus",
        "normative": "Refers to law, norms and principles",
        "assertive": "Strongly defends positions or criticizes others",
    }

    RISK_EXPLAIN = {
        "low": "Avoids sensitive issues",
        "medium": "Occasionally addresses sensitive issues",
        "high": "Frequently addresses sensitive or controversial issues",
    }

    # toggle (persistent)
    st.session_state.show_contextual = st.toggle(
        "Show contextual signals",
        value=st.session_state.show_contextual
    )

    if st.session_state.show_contextual:
        left, right = st.columns([2, 1], vertical_alignment="top")
    else:
        left = st.container()
        right = None

    # ----------------------------
    # LEFT: baseline country profile
    # ----------------------------
    with left:
        c1, c2, c3 = st.columns(3)

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
                profile["risk_profile"]["risk_tolerance"],
                help=RISK_EXPLAIN.get(profile["risk_profile"]["risk_tolerance"], "")
            )

        st.divider()

        st.markdown("### Main themes")
        for t, n in sorted(
            profile["topics"]["central"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]:
            st.write(f"- **{t}** ({n} mentions)")

        st.divider()

        with st.expander("📎 View all interventions"):
            for e in country_entries:
                st.markdown(f"**{e.get('date')} — {e.get('conference')}**")

                if e.get("keywords"):
                    st.caption("Keywords: " + ", ".join(e["keywords"]))

                if e.get("signals_text"):
                    st.markdown(f"> {e['signals_text']}")

                st.markdown("---")

    # ----------------------------
    # RIGHT: contextual signals panel (Block 2.5)
    # ----------------------------
    if right is not None:
        with right:
            st.markdown("### Contextual signals")

            rows = [r for r in block2_5_by_country.get(selected_country, []) if r.get("contextual_signal")]
            high_like = sum(
                1 for r in rows
                if any(v == "high" for v in (r.get("contextual_signals") or {}).values())
            )

            st.metric("Signals in scope", len(rows))
            st.metric("High-severity entries", high_like)

            if not rows:
                st.caption("No contextual deviations detected in current scope.")
            else:
                st.caption("Entries that deviate from the country baseline.")

                # Build a quick map entry_id -> entry for snippets/keywords/date
                entry_map = {}
                for e in country_entries:
                    eid = str(e.get("entry_id") or e.get("id") or e.get("ID") or "")
                    if eid:
                        entry_map[eid] = e

                for r in rows:
                    eid = str(r.get("entry_id"))
                    sigs = r.get("contextual_signals", {}) or {}

                    entry = entry_map.get(eid, {})
                    date = entry.get("date", "—")

                    # compact severity label
                    sev = "high" if any(v == "high" for v in sigs.values()) else "medium/low"

                    title = f"{date} · entry {eid} · {sev}"
                    with st.expander(title):
                        st.markdown("**Signals**")
                        st.json(sigs)

                        if r.get("rationale"):
                            st.markdown("**Rationale**")
                            for line in r["rationale"]:
                                st.markdown(f"- {line}")

                        kws = entry.get("keywords") or []
                        if kws:
                            st.markdown("**Keywords**")
                            st.caption(", ".join(kws))

                        if entry.get("signals_text"):
                            st.markdown("**Signal text**")
                            st.markdown(f"> {entry['signals_text']}")

            # Optional lightweight debug summary (kept minimal)
            with st.expander("Debug summary (Block 2.5)"):
                st.json(block2_5_dbg.get("global", {}))
