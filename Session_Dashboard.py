# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from shared.bootstrap import PROJECT_ROOT
from analysis.layers.block5_session_overview import analyze_session_overview


# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="Dashboard",
    layout="wide",
)

CANONICAL_PATH = PROJECT_ROOT / "canonical" / "canonical.jsonl"
EDITOR_PAGE = "pages/01_Editor.py"
CANONICAL_PAGE = "pages/06_Canonical.py"


# ==================================================
# DATA LOAD
# ==================================================

@st.cache_data(show_spinner=False)
def load_canonical(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def canonical_to_df(entries: List[Dict[str, Any]]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    for e in entries:
        micro = e.get("micro_analysis") or {}
        sp = e.get("speaker_structure") or {}
        ps = sp.get("primary_speaker") or {}

        speaker = ps.get("name") or sp.get("speaker_raw") or ""
        country = ps.get("country") or speaker

        if not country or country.lower() == "unknown":
            continue

        topics = micro.get("topics_analysis") or {}

        acts = micro.get("diplomatic_acts") or {}

        rows.append({
            "entry_id": e.get("entry_id"),
            "date": pd.to_datetime(e.get("date"), errors="coerce"),
            "conference": e.get("conference") or "",
            "country": country,
            "risk_level": micro.get("risk_level") or "",
            "watch_flag": bool(micro.get("watch_flag")),
            "signals_text": e.get("signals_text") or "",
            "central_topics": topics.get("central_topics") or [],
            "secondary_topics": topics.get("secondary_topics") or [],
            "diplomatic_posture": micro.get("diplomatic_posture") or "",
            "discursive_gesture": micro.get("discursive_gesture") or "",
            "explicitness_level": micro.get("explicitness_level") or "",
            "act_announcement": bool(acts.get("announcement")),
            "act_candidacy": bool(acts.get("candidacy")),
            "act_initiative_launch": bool(acts.get("initiative_launch")),
            "act_invitation": bool(acts.get("invitation")),
            "act_report_reference": bool(acts.get("report_reference")),
            "act_procedural_opening": bool(acts.get("procedural_opening")),
        })

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["date"])
    return df


# ==================================================
# ALERT MODEL
# ==================================================

@dataclass
class AlertItem:
    severity: str
    title: str
    subtitle: str
    entries: List[Dict[str, Any]]


def build_live_alerts(
    df_scope: pd.DataFrame,
    now: pd.Timestamp,
    window_days: int = 3,
    max_items: int = 3,
) -> List[AlertItem]:

    alerts: List[AlertItem] = []

    if df_scope.empty or pd.isna(now):
        return alerts

    df_w = df_scope[df_scope["date"] >= now - timedelta(days=window_days)]

    high_df = df_w[df_w["risk_level"] == "high"]
    if len(high_df) >= max(5, int(0.25 * len(df_w))):
        alerts.append(
            AlertItem(
                severity="critical",
                title="High-risk burst",
                subtitle=f"{len(high_df)} high-risk entries (last {window_days}d)",
                entries=high_df.sort_values("date", ascending=False)
                .head(max_items)
                .to_dict("records"),
            )
        )

    watch_df = df_w[df_w["watch_flag"]]
    if len(watch_df) >= max(5, int(0.30 * len(df_w))):
        alerts.append(
            AlertItem(
                severity="high",
                title="Watch-flag surge",
                subtitle=f"{len(watch_df)} watch entries (last {window_days}d)",
                entries=watch_df.sort_values("date", ascending=False)
                .head(max_items)
                .to_dict("records"),
            )
        )

    vc = df_w["country"].value_counts()
    if not vc.empty and vc.iloc[0] >= 3:
        actor = vc.index[0]
        df_a = df_w[df_w["country"] == actor]
        alerts.append(
            AlertItem(
                severity="high",
                title="Repeated actor",
                subtitle=f"{actor} appears {len(df_a)} times (last {window_days}d)",
                entries=df_a.sort_values("date", ascending=False)
                .head(max_items)
                .to_dict("records"),
            )
        )

    return alerts


# ==================================================
# ANALYTICS HELPERS
# ==================================================

def weighted_topics(df: pd.DataFrame, top_n: int = 5) -> Dict[str, int]:
    c = Counter()
    for _, r in df.iterrows():
        for t in r["central_topics"]:
            c[t] += 3
        for t in r["secondary_topics"]:
            c[t] += 1
    return dict(c.most_common(top_n))


def build_timeline(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.dropna(subset=["date"])
    day = tmp["date"].dt.date
    return pd.DataFrame({
        "total": tmp.groupby(day).size(),
        "high_risk": tmp[tmp["risk_level"] == "high"].groupby(day).size(),
        "watch": tmp[tmp["watch_flag"]].groupby(day).size(),
    }).fillna(0)


# ==================================================
# LOAD DATA
# ==================================================

entries = load_canonical(CANONICAL_PATH)
df = canonical_to_df(entries)

if df.empty:
    st.error("No valid canonical data found.")
    st.stop()

sessions = sorted(s for s in df["conference"].unique() if s.strip())


# ==================================================
# HEADER
# ==================================================

left, right = st.columns([4.8, 1.5])

with left:
    st.title("Dashboard")
    st.caption("Canonical-driven · analyst-first · live session intelligence")

with right:
    b1, b2 = st.columns(2)

    b1.page_link(
        EDITOR_PAGE,
        label="✍️ Editor",
        use_container_width=True,
    )

    b2.page_link(
        CANONICAL_PAGE,
        label="📓 Canonical",
        use_container_width=True,
    )

# ==================================================
# VIEW MODE
# ==================================================

view_mode = st.radio(
    "View mode",
    ["🧠 Session view", "📅 Temporal view"],
    horizontal=True,
)

st.divider()


# ==================================================
# SESSION VIEW
# ==================================================

if view_mode == "🧠 Session view":

    main, alerts_col = st.columns([3, 1], gap="large")

    with main:
        session = st.selectbox("Session", sessions)
        df_s = df[df["conference"] == session]

        st.info(
            f"Session **{session}** · "
            f"{len(df_s)} entries · "
            f"{df_s['country'].nunique()} actors · "
            f"Last update: {df_s['date'].max().date()}"
        )

        b5 = analyze_session_overview(session, PROJECT_ROOT)
        ov = b5.get("session_overview", {})
        sr = b5.get("strategic_reading", {})

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Entries", len(df_s))
        m2.metric("Fragmentation", str(ov.get("fragmentation_level", "—")).upper())
        m3.metric("Institutional density", str(ov.get("institutional_density", "—")).upper())
        m4.metric("Spillover risk", str(sr.get("spillover_risk", "—")).upper())

        hi_3d = int((df_s[df_s["date"] >= df_s["date"].max() - timedelta(days=3)]["risk_level"] == "high").sum())
        watch_3d = int(df_s[df_s["date"] >= df_s["date"].max() - timedelta(days=3)]["watch_flag"].sum())

        st.info(
            "🧠 **Session reading**\n\n"
            f"- **Fragmentation:** {str(ov.get('fragmentation_level','—')).upper()} · {df_s['country'].nunique()} actors\n"
            f"- **Spillover proxy:** {hi_3d} high-risk entries (last 3 days)\n"
            f"- **Watch pressure:** {watch_3d} watch entries (last 3 days)"
        )

        agenda = sr.get("agenda_drivers", [])
        if agenda:
            st.markdown("**Agenda drivers**")
            cols = st.columns(min(len(agenda), 5))
            for c, a in zip(cols, agenda[:5]):
                c.markdown(f"`{a}`")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Risk distribution")
            rd = df_s["risk_level"].value_counts()
            st.bar_chart(
                {"High": rd.get("high", 0), "Medium": rd.get("medium", 0), "Low": rd.get("low", 0)},
                horizontal=True,
            )

        with c2:
            st.subheader("Watch status")
            w = int(df_s["watch_flag"].sum())
            n = len(df_s) - w
            p = int(100 * w / max(1, w + n))
            a, b, c = st.columns(3)
            a.metric("Watch", w)
            b.metric("Non-watch", n)
            c.metric("Watch %", f"{p}%")

        st.divider()

        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Top topics (weighted · top 5)")
            tt = weighted_topics(df_s)
            if tt:
                st.bar_chart(tt, horizontal=True)

        with c4:
            st.subheader("Top actors (top 8)")
            ta = df_s["country"].value_counts().head(8)
            st.bar_chart(ta, horizontal=True)

        st.divider()

        st.subheader("Timeline (volume · high-risk · watch)")
        st.line_chart(build_timeline(df_s))

        st.divider()

        # --------------------------------------------------
        # MICRO SIGNALS
        # --------------------------------------------------

        st.subheader("Micro signals")

        ms1, ms2, ms3 = st.columns(3)

        with ms1:
            st.markdown("**Diplomatic posture**")
            posture_order = ["assertive", "cooperative", "passive", "procedural"]
            pc = df_s["diplomatic_posture"].value_counts()
            pc = pc.reindex([p for p in posture_order if p in pc.index])
            if not pc.empty:
                st.bar_chart(pc, horizontal=True)

        with ms2:
            st.markdown("**Discursive gesture**")
            gc = df_s["discursive_gesture"].value_counts()
            if not gc.empty:
                st.bar_chart(gc, horizontal=True)

        with ms3:
            st.markdown("**Explicitness**")
            exp_order = ["high", "medium", "low"]
            ec = df_s["explicitness_level"].value_counts()
            ec = ec.reindex([e for e in exp_order if e in ec.index])
            if not ec.empty:
                st.bar_chart(ec, horizontal=True)

        st.divider()

        # Vigilance table: assertive + high explicitness
        vigilance = df_s[
            (df_s["diplomatic_posture"] == "assertive") &
            (df_s["explicitness_level"] == "high")
        ][["country", "risk_level", "watch_flag", "central_topics", "signals_text"]] \
            .sort_values("risk_level", ascending=False)

        if not vigilance.empty:
            st.markdown(f"**Vigilance — assertive + high explicitness ({len(vigilance)} entries)**")
            st.caption("These entries combine an assertive posture with explicit framing — highest signal density.")
            for _, r in vigilance.head(8).iterrows():
                topics_str = ", ".join(r["central_topics"]) if r["central_topics"] else "—"
                st.markdown(
                    f"**{r['country']}** · `{r['risk_level']}` · "
                    f"{'👁️' if r['watch_flag'] else ''} · {topics_str}"
                )
                with st.expander("Signal text"):
                    st.write(r["signals_text"])
        else:
            st.caption("No assertive + high-explicitness entries in this session.")

        st.divider()

        # Diplomatic acts
        act_cols = {
            "act_initiative_launch": "Initiative launch",
            "act_candidacy": "Candidacy",
            "act_invitation": "Invitation",
            "act_announcement": "Announcement",
            "act_report_reference": "Report reference",
            "act_procedural_opening": "Procedural opening",
        }

        act_rows = []
        for col, label in act_cols.items():
            actors = df_s[df_s[col]]["country"].value_counts()
            for country_name, count in actors.items():
                act_rows.append({"Act": label, "Country": country_name, "Count": int(count)})

        if act_rows:
            st.markdown("**Diplomatic acts detected**")
            st.caption("Discrete acts only — blank = none detected.")
            act_df = pd.DataFrame(act_rows).sort_values(["Act", "Count"], ascending=[True, False])
            st.dataframe(act_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No discrete diplomatic acts detected in this session.")

        st.divider()

        st.subheader("Latest signals")
        for _, r in df_s.sort_values("date", ascending=False).head(10).iterrows():
            st.markdown(
                f"**{r['country']}** · `{r['risk_level']}` · "
                f"{'👁️ watch' if r['watch_flag'] else ''} · `{r['entry_id']}`"
            )
            with st.expander("Show signals text"):
                st.write(r["signals_text"])

    with alerts_col:
        st.subheader("🔔 Alerts (actionable)")

        alerts = build_live_alerts(df_s, df_s["date"].max())

        if not alerts:
            st.success("No critical alerts.")
        else:
            for a_idx, al in enumerate(alerts):
                box = st.error if al.severity == "critical" else st.warning
                box(f"**{al.title}** — {al.subtitle}")

                with st.expander("Details"):
                    for e_idx, e in enumerate(al.entries):
                        cols = st.columns([2.4, 1.0, 0.8, 0.6])
                        cols[0].markdown(f"**{e['country']}**")
                        cols[1].markdown(e["risk_level"])
                        cols[2].markdown("👁️" if e["watch_flag"] else "—")
                        cols[3].page_link(
                            CANONICAL_PAGE,
                            label="↗",
                            query_params={"q": e["entry_id"]},
                            help="Open in Canonical",
                        )


# ==================================================
# TEMPORAL VIEW
# ==================================================

else:
    main, alerts_col = st.columns([3, 1], gap="large")

    with main:
        st.subheader("Temporal monitoring")

        f1, f2, f3 = st.columns([1.1, 1.1, 1.4])
        with f1:
            d_from = st.date_input("From", df["date"].min().date())
        with f2:
            d_to = st.date_input("To", df["date"].max().date())
        with f3:
            conf_sel = st.multiselect("Conference", sessions, default=[])

        if d_from > d_to:
            st.error("Invalid date range.")
            st.stop()

        df_t = df[(df["date"].dt.date >= d_from) & (df["date"].dt.date <= d_to)].copy()
        if conf_sel:
            df_t = df_t[df_t["conference"].isin(conf_sel)]

        st.info(
            f"Period **{d_from} → {d_to}** · "
            f"{len(df_t)} entries · "
            f"{df_t['country'].nunique()} actors"
        )

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Risk distribution")
            rd = df_t["risk_level"].value_counts()
            st.bar_chart(
                {"High": rd.get("high", 0), "Medium": rd.get("medium", 0), "Low": rd.get("low", 0)},
                horizontal=True,
            )

        with c2:
            st.subheader("Watch status")
            w = int(df_t["watch_flag"].sum())
            n = len(df_t) - w
            p = int(100 * w / max(1, w + n))
            a, b, c = st.columns(3)
            a.metric("Watch", w)
            b.metric("Non-watch", n)
            c.metric("Watch %", f"{p}%")

        st.divider()

        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Top topics (weighted · top 5)")
            tt = weighted_topics(df_t)
            if tt:
                st.bar_chart(tt, horizontal=True)

        with c4:
            st.subheader("Top actors (top 8)")
            ta = df_t["country"].value_counts().head(8)
            st.bar_chart(ta, horizontal=True)

        st.divider()

        st.subheader("Timeline (volume · high-risk · watch)")
        st.line_chart(build_timeline(df_t))

        st.divider()

        st.subheader("Latest signals")
        for _, r in df_t.sort_values("date", ascending=False).head(12).iterrows():
            st.markdown(
                f"**{r['country']}** · `{r['risk_level']}` · "
                f"{'👁️ watch' if r['watch_flag'] else ''} · `{r['entry_id']}`"
            )
            with st.expander("Show signals text"):
                st.write(r["signals_text"])

    with alerts_col:
        st.subheader("🔔 Alerts (temporal)")

        alerts = build_live_alerts(df_t, df_t["date"].max())

        if not alerts:
            st.success("No critical alerts.")
        else:
            for a_idx, al in enumerate(alerts):
                box = st.error if al.severity == "critical" else st.warning
                box(f"**{al.title}** — {al.subtitle}")

                with st.expander("Details"):
                    for e_idx, e in enumerate(al.entries):
                        cols = st.columns([2.4, 1.0, 0.8, 0.6])
                        cols[0].markdown(f"**{e['country']}**")
                        cols[1].markdown(e["risk_level"])
                        cols[2].markdown("👁️" if e["watch_flag"] else "—")
                        cols[3].page_link(
                            CANONICAL_PAGE,
                            label="↗",
                            query_params={"q": e["entry_id"]},
                            help="Open in Canonical",
                       )
