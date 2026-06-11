from __future__ import annotations
import streamlit as st
from typing import Any, Dict, List, Optional, Tuple


def section(title: str, description: str):
    st.markdown(
        f"""
<div class="section-card">
  <div class="card-title">{title}</div>
  <div class="card-desc">{description}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _format_value_human(value: Any, unit: Optional[str] = None) -> str:
    if isinstance(value, bool):
        return "Enabled" if value else "Disabled"
    if isinstance(value, list):
        if len(value) == 0:
            return "No values configured"
        if len(value) == 1:
            return "1 value configured"
        return f"{len(value)} values configured"
    if isinstance(value, (int, float)):
        return f"{value} {unit or ''}".strip()
    if value is None:
        return "Not set"
    s = str(value).strip()
    if len(s) > 120:
        return s[:120] + "…"
    return s


def _render_meta(meta: Dict[str, Any]):
    if not meta:
        return

    if meta.get("description"):
        st.markdown(f"<div class='card-desc'>{meta['description']}</div>", unsafe_allow_html=True)

    unit = meta.get("unit")
    inc = meta.get("increase_effect")
    dec = meta.get("decrease_effect")

    kpis = []
    if unit:
        kpis.append(f"Unit: {unit}")
    if inc:
        kpis.append(f"If increased: {inc}")
    if dec:
        kpis.append(f"If decreased: {dec}")

    if kpis:
        st.markdown("<div class='kpi-row'>" + "".join([f"<span class='kpi'>{k}</span>" for k in kpis]) + "</div>", unsafe_allow_html=True)


def question_card(
    key: str,
    title: str,
    description: str,
    current_value: Any,
    meta: Dict[str, Any],
    allow_type_change: bool = True,
) -> Tuple[bool, Any]:
    """
    Returns (did_save, new_value)
    """
    edit_flag = f"edit::{key}"
    editing = st.session_state.get(edit_flag, False)

    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{title}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-desc'>{description}</div>", unsafe_allow_html=True)

        # Add meta help (unit/inc/dec + optional description)
        _render_meta(meta)

        # READ MODE
        if not editing:
            st.markdown("<div class='card-current'>Current setting</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='card-value'>{_format_value_human(current_value, meta.get('unit'))}</div>",
                unsafe_allow_html=True,
            )

            cols = st.columns([1, 5])
            with cols[0]:
                if st.button("Edit", key=f"btn_edit::{key}"):
                    st.session_state[edit_flag] = True

            st.markdown("</div>", unsafe_allow_html=True)
            return False, None

        # EDIT MODE
        st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
        st.markdown("<div class='card-current'>Edit value</div>", unsafe_allow_html=True)

        # initial type
        if isinstance(current_value, bool):
            initial_type = "On / Off"
        elif isinstance(current_value, list):
            initial_type = "List"
        elif isinstance(current_value, (int, float)):
            initial_type = "Number"
        else:
            initial_type = "Text"

        type_choices = ["Number", "On / Off", "List", "Text"]
        idx = type_choices.index(initial_type)

        if allow_type_change:
            chosen_type = st.selectbox("Value type", type_choices, index=idx, key=f"type::{key}")
        else:
            chosen_type = initial_type

        # Editor per type (human inputs only, no YAML)
        new_value: Any = current_value

        if chosen_type == "Number":
            base = int(current_value) if isinstance(current_value, (int, float)) else 0
            new_value = st.number_input(
                "Value",
                value=base,
                step=1,
                label_visibility="collapsed",
                key=f"num::{key}",
            )

        elif chosen_type == "On / Off":
            new_value = st.toggle(
                "Enabled",
                value=bool(current_value),
                label_visibility="collapsed",
                key=f"bool::{key}",
            )

        elif chosen_type == "List":
            values = list(current_value) if isinstance(current_value, list) else []
            edited: List[str] = []
            for i, v in enumerate(values):
                edited.append(st.text_input(f"Value {i+1}", value=str(v), key=f"list::{key}::{i}"))

            add_cols = st.columns([1, 3])
            with add_cols[0]:
                if st.button("Add value", key=f"add_value::{key}"):
                    edited.append("")
            with add_cols[1]:
                st.caption("Empty rows will be ignored when saving.")

            new_value = [v.strip() for v in edited if v.strip()]

        else:  # Text
            text = "" if current_value is None else str(current_value)
            new_value = st.text_area(
                "Value",
                value=text,
                height=120,
                label_visibility="collapsed",
                key=f"text::{key}",
            )

        btn1, btn2, btn3 = st.columns([1, 1, 4])
        with btn1:
            if st.button("Cancel", key=f"cancel::{key}"):
                st.session_state[edit_flag] = False
                st.markdown("</div>", unsafe_allow_html=True)
                return False, None
        with btn2:
            if st.button("Save", key=f"save::{key}"):
                st.session_state[edit_flag] = False
                st.markdown("</div>", unsafe_allow_html=True)
                return True, new_value

        st.markdown("</div>", unsafe_allow_html=True)
        return False, None


def add_parameter_block(section_key: str) -> Tuple[bool, str, Any, str]:
    """
    Clean "Add parameter" drawer-like block.
    Returns (did_add, key, value, description)
    """
    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Add parameter</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card-desc'>Create a new parameter in this section. This is intended for advanced users.</div>",
            unsafe_allow_html=True,
        )

        k = st.text_input("Parameter key", key=f"addkey::{section_key}")
        v = st.text_input("Initial value", key=f"addval::{section_key}", help="Use plain text. You can switch type after creation.")
        d = st.text_area("Short description (optional)", key=f"adddesc::{section_key}", height=90)

        btn = st.button("Add parameter", key=f"addbtn::{section_key}")
        st.markdown("</div>", unsafe_allow_html=True)

    if not btn:
        return False, "", None, ""
    if not k.strip():
        st.warning("Parameter key is required.")
        return False, "", None, ""
    # Default value is text; user can change type later by editing
    return True, k.strip(), v, d.strip()
