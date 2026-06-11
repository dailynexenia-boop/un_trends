from __future__ import annotations


import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import csv
from datetime import date
from typing import List

from shared.bootstrap import PROJECT_ROOT
from ingest.ingest_row import build_manual_entry
from utils.canonical_io import append_jsonl
from analysis.recompute_canonical import (
    recompute_pending_only,
    recompute_all,
)

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(
    page_title="Intervention Editor",
    layout="wide",
)

CANONICAL_PATH = Path("canonical/canonical.jsonl")
RAW_DIR = Path("raw")
RAW_DIR.mkdir(exist_ok=True)

# ==================================================
# HELPERS
# ==================================================
def split_keywords(raw: str) -> List[str]:
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def reset_manual_form():
    for key in [
        "date_value",
        "conf",
        "session_label",
        "speaker_raw",
        "signals_text",
        "keywords_raw",
    ]:
        st.session_state.pop(key, None)


def append_raw_csv(path: Path, row: dict):
    file_exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# ==================================================
# UI
# ==================================================
st.title("Intervention Editor")
st.caption(
    "Saisie manuelle ou import CSV d’interventions. "
    "Ingestion append-only · RAW sauvegardé avant analyse."
)

tab_manual, tab_csv = st.tabs(["Manual entry", "CSV upload"])

# ==================================================
# TAB 1 — MANUAL ENTRY
# ==================================================
with tab_manual:
    left, right = st.columns([1, 1], gap="large")

    # -------------------------
    # FORM
    # -------------------------
    with left:
        st.subheader("Manual entry")

        with st.form("manual_form", clear_on_submit=False):
            date_value = st.date_input(
                "Date",
                value=st.session_state.get("date_value", date.today()),
                key="date_value",
            )

            conference = st.text_input(
                "Conference",
                placeholder="HRC 60",
                key="conf",
            )

            session_label = st.text_input(
                "Session label",
                placeholder="General Debate – Item 4",
                key="session_label",
            )

            speaker_raw = st.text_input(
                "Speaker (raw)",
                placeholder="Country / group / institution",
                key="speaker_raw",
            )

            signals_text = st.text_area(
                "Intervention text",
                height=300,
                placeholder="Paste or type the intervention text here.",
                key="signals_text",
            )

            keywords_raw = st.text_input(
                "Keywords (comma-separated)",
                placeholder="keyword1, keyword2, keyword3",
                key="keywords_raw",
            )

            col_submit, col_reset = st.columns(2)
            submit_manual = col_submit.form_submit_button(
                "Save entry",
                use_container_width=True,
            )
            reset_manual = col_reset.form_submit_button(
                "Reset form",
                use_container_width=True,
            )

        if reset_manual:
            reset_manual_form()
            st.rerun()

        if submit_manual:
            if not speaker_raw or not signals_text:
                st.error("Speaker and intervention text are required.")
            else:
                try:
                    # ---- RAW SAVE (SAFE FIRST)
                    raw_row = {
                        "date": date_value.isoformat(),
                        "conference": conference,
                        "session_label": session_label,
                        "speaker_raw": speaker_raw,
                        "signals_text": signals_text,
                        "keywords": keywords_raw,
                    }

                    raw_path = RAW_DIR / f"manual_{date.today().isoformat()}.csv"
                    append_raw_csv(raw_path, raw_row)

                    # ---- CANONICAL + ANALYSIS
                    entry = build_manual_entry(
                        date=date_value,
                        conference=conference,
                        session_label=session_label,
                        speaker_raw=speaker_raw,
                        signals_text=signals_text,
                        keywords=split_keywords(keywords_raw),
                    )

                    append_jsonl(CANONICAL_PATH, entry)
                    n = recompute_pending_only()

                    st.success("Entry successfully saved.")
                    st.caption(f"RAW snapshot saved → {raw_path.name}")
                    st.caption(f"Analytical pipeline applied to {n} entry(ies).")
                    st.caption(f"New entry_id: {entry['entry_id']}")

                except Exception as e:
                    st.error("Error while saving the entry.")
                    st.exception(e)

    # -------------------------
    # PREVIEW
    # -------------------------
    with right:
        st.subheader("Preview")
        st.caption("Aperçu lisible (aucun JSON affiché).")

        st.markdown("**Conference**")
        st.write((st.session_state.get("conf") or "").strip() or "—")

        st.markdown("**Session label**")
        st.write((st.session_state.get("session_label") or "").strip() or "—")

        st.markdown("**Speaker (raw)**")
        st.write((st.session_state.get("speaker_raw") or "").strip() or "—")

        st.markdown("**Keywords**")
        st.write((st.session_state.get("keywords_raw") or "").strip() or "—")

        st.markdown("**Intervention text**")
        st.write((st.session_state.get("signals_text") or "").strip() or "—")

# ==================================================
# TAB 2 — CSV UPLOAD
# ==================================================
with tab_csv:
    st.subheader("CSV upload")
    st.caption(
        "Import d’un CSV. Chaque ligne est sauvegardée en RAW "
        "avant ingestion canonique."
    )

    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=["csv"],
        accept_multiple_files=False,
    )

    if uploaded_file:
        rows = list(
            csv.DictReader(
                uploaded_file.read().decode("utf-8-sig").splitlines()
            )
        )

        st.info(
            f"{len(rows)} rows detected · "
            f"{len(rows[0].keys()) if rows else 0} columns"
        )

        if st.button("Ingest CSV"):
            success = 0
            errors = 0

            raw_path = RAW_DIR / f"csv_upload_{date.today().isoformat()}.csv"

            for idx, row in enumerate(rows, start=1):
                try:
                    # ---- RAW SAVE
                    append_raw_csv(raw_path, row)

                    # ---- CANONICAL
                    entry = build_manual_entry(
                        date=date.fromisoformat(row["Date"]),
                        conference=row["Conference"],
                        session_label=row["Session"],
                        speaker_raw=row["Country"],
                        signals_text=row["Signals"],
                        keywords=split_keywords(row.get("Keywords", "")),
                    )

                    append_jsonl(CANONICAL_PATH, entry)
                    success += 1

                except Exception as e:
                    errors += 1
                    st.error(f"Row {idx} failed: {e}")

            st.success(f"CSV ingestion completed: {success} entries added.")
            st.caption(f"RAW snapshot saved → {raw_path.name}")
            if errors:
                st.warning(f"{errors} rows failed.")

# ==================================================
# ANALYTICAL DOCTRINE
# ==================================================
st.divider()
st.subheader("Analytical doctrine")
st.caption(
    "Apply or refresh analytical layers "
    "(speaker structure, micro-analysis)."
)

col1, col2 = st.columns(2)

with col1:
    if st.button("Recompute pending entries"):
        n = recompute_pending_only()
        st.success(f"{n} pending entries recomputed.")

with col2:
    if st.button("Recompute ALL entries (admin)"):
        n = recompute_all()
        st.warning(f"ALL entries recomputed ({n}).")

# ==================================================
# FOOTER
# ==================================================
st.divider()
st.caption(f"Canonical path: {CANONICAL_PATH.resolve()}")
st.caption(f"RAW directory: {RAW_DIR.resolve()}")
