from __future__ import annotations

# ==================================================
# BOOTSTRAP PROJECT ROOT (UI ENTRY POINT)
# ==================================================
import sys
from pathlib import Path
from shared.bootstrap import PROJECT_ROOT

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ==================================================
# STANDARD IMPORTS
# ==================================================
import streamlit as st
import pandas as pd
import json

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Canonical Log",
    layout="wide",
)

# =====================================================
# STYLE – DARK AUDIT THEME
# =====================================================

st.markdown(
    """
<style>
:root {
    --bg-main: #0F1115;
    --accent: #2A2E35;
    --text-main: #D6D7D9;
}

html, body, [data-testid="stApp"] {
    background-color: var(--bg-main);
    color: var(--text-main);
}

section[data-testid="stSidebar"] {
    display: none;
}

.stDataFrame {
    border: 1px solid var(--accent);
}

label, .stMarkdown {
    color: var(--text-main) !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# =====================================================
# LOAD CANONICAL
# =====================================================

CANONICAL_PATH = PROJECT_ROOT / "canonical" / "canonical.jsonl"

@st.cache_data
def load_entries(path: Path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f]

if st.button("Reload canonical"):
    st.cache_data.clear()

entries = load_entries(CANONICAL_PATH)

# =====================================================
# HEADER + SEARCH
# =====================================================

st.title("Canonical debug log")
st.caption("Audit-first · search-driven · no JSON leakage")

st.markdown(f"**Total canonical entries:** {len(entries)}")

search_id = st.text_input(
    "Search by entry_id",
    placeholder="Paste full or partial entry_id",
)

# =====================================================
# LANDING STATE → TABLE
# =====================================================

if not search_id:
    df = pd.DataFrame([
        {
            "entry_id": e.get("entry_id"),
            "date": e.get("date"),
            "conference": e.get("conference"),
            "session": e.get("session_label"),
            "speaker_raw": e.get("speaker_structure", {}).get("speaker_raw"),
            "keywords": ", ".join(e.get("keywords", [])),
        }
        for e in entries
    ])

    st.subheader("Canonical entries (audit table)")
    st.dataframe(df, use_container_width=True, height=600)

# =====================================================
# SEARCH STATE → ENTRY DETAIL
# =====================================================

else:
    matches = [
        e for e in entries
        if search_id.lower() in (e.get("entry_id") or "").lower()
    ]

    if not matches:
        st.warning("No matching entry found.")
    else:
        st.subheader("Entry detail")

        for entry in matches:
            sp = entry.get("speaker_structure", {})
            ps = sp.get("primary_speaker", {})
            micro = entry.get("micro_analysis", {})
            topics = micro.get("topics_analysis", {})

            # ---- Core
            st.markdown("### Core")
            st.write(entry.get("entry_id"))
            st.write(entry.get("date"))
            st.write(entry.get("conference"))
            st.write(entry.get("session_label"))

            # ---- Speaker
            st.markdown("### Speaker")
            st.write(f"**Raw:** {sp.get('speaker_raw')}")
            st.write(f"**Primary speaker:** {ps.get('name')}")
            st.write(f"**State:** {ps.get('is_state')}")
            st.write(f"**Institution:** {ps.get('is_institution')}")
            st.write(f"**Alignment group:** {ps.get('is_alignment_group')}")
            st.write(f"**Regional group:** {ps.get('regional_group')}")
            st.write(f"**Coalition:** {sp.get('coalition', {}).get('is_coalition')}")
            st.write(f"**Alignment groups:** {', '.join(sp.get('alignment_groups', []))}")

            # ---- Raw content
            st.markdown("### Raw content")
            st.write("**Signals text:**")
            st.write(entry.get("signals_text"))
            st.write("**Keywords:**")
            st.write(", ".join(entry.get("keywords", [])))

            # ---- Micro analysis
            st.markdown("### Micro analysis")
            st.write(f"**Central topics:** {', '.join(topics.get('central_topics', []))}")
            st.write(f"**Secondary topics:** {', '.join(topics.get('secondary_topics', []))}")
            st.write(f"**Diplomatic posture:** {micro.get('diplomatic_posture')}")
            st.write(f"**Explicitness level:** {micro.get('explicitness_level')}")
            st.write(f"**Risk level:** {micro.get('risk_level')}")
            st.write(
                "**Diplomatic acts:** "
                + ", ".join(k for k, v in micro.get("diplomatic_acts", {}).items() if v)
            )
            st.write(f"**Watch flag:** {micro.get('watch_flag')}")

            st.divider()
