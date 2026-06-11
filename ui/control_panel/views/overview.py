import streamlit as st
from pathlib import Path
from typing import Dict, Any


def render(
    config_dir: Path,
    ui_desc: Dict[str, Any],
    project_root: Path,
    snapshot_dir: Path,
):
    st.subheader("Overview")
    st.caption(
        "This page does not modify any configuration. "
        "Use the navigation menu to access specific configuration areas."
    )

    st.markdown("### Configuration Sections")

    st.markdown(
        """
- **Analysis Logic**  
  Controls upstream analytical logic (micro-analysis, detection rules).

- **Registers**  
  Manages shared reference lists used across the system.

- **Analytical Core**  
  Governs strategic analytical configuration (Block 4).  
  Changes made here modify `block4.yaml`.

- **UI Configuration**  
  Controls interface-related settings (labels, layout, presentation).

- **LLM & Projections**  
  Reserved for language-model-based projections (not fully configured yet).

- **Recompute & History**  
  Applies configuration changes and provides access to configuration snapshots.
"""
    )

    st.markdown("### Notes")
    st.markdown(
        """
- Configuration changes only take effect after recomputation.
- All configuration files are versioned automatically.
- This page is informational only.
"""
    )
