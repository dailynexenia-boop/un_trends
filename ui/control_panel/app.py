import sys
from pathlib import Path
import streamlit as st

ROOT = Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.control_panel.core.styles import apply_styles
from ui.control_panel.core.store import get_paths
from ui.control_panel.core.ui_meta import load_ui_descriptions

from ui.control_panel.views import (
    overview,
    analysis_logic,
    analytical_core,
    ui_configuration,
    llm_projections,
    registers,
    signal_detection,
    raw_editor,
    recompute_history,
)



def main():
    apply_styles()

    paths = get_paths(__file__)
    ui_desc = load_ui_descriptions(paths.config_dir / "ui_descriptions.yaml")

    st.title("Control Panel")
    st.caption(
        "Configuration and governance interface intended to be embedded within a broader application."
    )

    st.sidebar.markdown(
        "<div class='sidebar-title'>Navigation</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div class='sidebar-sub'>Select a configuration area</div>",
        unsafe_allow_html=True,
    )

     
    if "nav_target" not in st.session_state:
        st.session_state.nav_target = "Overview"

    PAGES = [
        "Overview",
        "Analysis Logic",
        "Signal Detection",
        "Registers",
        "Analytical Core",
        "UI Configuration",
        "LLM & Projections",
        "Raw Editor",
        "Recompute & History",
    ]

    page = st.sidebar.radio(
        "Page",
        PAGES,
        index=PAGES.index(st.session_state.nav_target) if st.session_state.nav_target in PAGES else 0,
        key="page_radio",
        label_visibility="collapsed",
    )

    # Sync radio → nav_target
    st.session_state.nav_target = page

    if page == "Overview":
        overview.render(
            paths.config_dir,
            ui_desc,
            paths.project_root,
            paths.snapshot_dir,
        )

    elif page == "Analysis Logic":
        analysis_logic.render(
            paths.config_dir,
            ui_desc,
            paths.project_root,
            paths.snapshot_dir,
        )

    elif page == "Signal Detection":
        signal_detection.render(
            paths.config_dir,
            ui_desc,
            paths.project_root,
            paths.snapshot_dir,
        )

    elif page == "Registers":
        registers.render(
            paths.config_dir,
            ui_desc,
            paths.project_root,
            paths.snapshot_dir,
        )

    elif page == "Analytical Core":
        analytical_core.render(
            paths.config_dir,
            ui_desc,
            paths.project_root,
            paths.snapshot_dir,
        )

    elif page == "UI Configuration":
        ui_configuration.render(
            paths.config_dir,
            ui_desc,
            paths.project_root,
            paths.snapshot_dir,
        )

    elif page == "LLM & Projections":
        llm_projections.render(
            paths.config_dir,
            ui_desc,
            paths.project_root,
            paths.snapshot_dir,
        )


    elif page == "Raw Editor":
        raw_editor.render(
            paths.config_dir,
            ui_desc,
            paths.project_root,
            paths.snapshot_dir,
        )

    else:  # Recompute & History
        recompute_history.render(
            paths.config_dir,
            ui_desc,
            paths.project_root,
            paths.snapshot_dir,
        )


if __name__ == "__main__":
    main()
