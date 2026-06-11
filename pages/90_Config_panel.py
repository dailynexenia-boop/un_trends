from __future__ import annotations
from shared.bootstrap import PROJECT_ROOT

import streamlit as st

st.set_page_config(page_title="Config panel", layout="wide")

from ui.control_panel.app import main
main()
