# -*- coding: utf-8 -*-
"""
Raw Editor — generic YAML editor with path picker, diff, and snapshot.
Covers any config file not exposed by dedicated views.
"""

from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any
import difflib
import yaml
import streamlit as st

from ui.control_panel.core.store import load_yaml, save_yaml, snapshot_yaml


# --------------------------------------------------
# Helpers (ported from config_app.py)
# --------------------------------------------------

def list_paths(data, prefix=""):
    paths = []
    if isinstance(data, dict):
        for k, v in data.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            paths.append(p)
            paths.extend(list_paths(v, p))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            p = f"{prefix}.{i}" if prefix else str(i)
            paths.append(p)
            paths.extend(list_paths(v, p))
    return paths


def get_node(data, tokens):
    node = data
    for t in tokens:
        if isinstance(node, dict):
            node = node.get(t)
        elif isinstance(node, list):
            try:
                node = node[int(t)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return node


def set_node(data, tokens, value):
    node = data
    for t in tokens[:-1]:
        node = node[t] if isinstance(node, dict) else node[int(t)]
    last = tokens[-1]
    if isinstance(node, dict):
        node[last] = value
    else:
        node[int(last)] = value


# --------------------------------------------------
# Page
# --------------------------------------------------

def render(
    config_dir: Path,
    ui_desc: Dict[str, Any],
    project_root: Path,
    snapshot_dir: Path,
):
    st.subheader("Raw Editor")
    st.caption(
        "Generic YAML editor — navigate any parameter in any config file. "
        "Changes are previewed with a diff before saving."
    )

    config_files = sorted(p.name for p in config_dir.glob("*.yaml"))
    selected_file = st.selectbox("Configuration file", config_files)
    config_path = config_dir / selected_file

    original = load_yaml(config_path)
    edited = deepcopy(original)

    all_paths = list_paths(original)
    q = st.text_input("Search key paths", placeholder="e.g. thresholds, temperature, watch_flag")
    filtered = [p for p in all_paths if q.lower() in p.lower()] if q else all_paths[:400]

    if not filtered:
        st.info("No matching paths.")
        return

    selected_path = st.selectbox("Select a parameter path", filtered)
    tokens = selected_path.split(".")
    node = get_node(edited, tokens)

    col_left, col_right = st.columns([1.4, 0.6], gap="large")

    with col_left:
        st.markdown(f"**Current value** — `{selected_path}`")
        st.code(yaml.safe_dump(node, allow_unicode=True, sort_keys=False), language="yaml")

        with st.expander("Diff (original vs edited)", expanded=False):
            new_text = yaml.safe_dump(edited, allow_unicode=True, sort_keys=False)
            old_text = yaml.safe_dump(original, allow_unicode=True, sort_keys=False)
            diff = "\n".join(difflib.unified_diff(
                old_text.splitlines(), new_text.splitlines(), lineterm=""
            ))
            st.code(diff if diff.strip() else "No changes.", language="diff")

    with col_right:
        st.markdown("**Edit**")

        if isinstance(node, bool):
            new_val = st.checkbox("Value", value=node, key="raw_bool")
            set_node(edited, tokens, new_val)

        elif isinstance(node, int):
            new_val = st.number_input("Value", value=node, step=1, format="%d", key="raw_int")
            set_node(edited, tokens, int(new_val))

        elif isinstance(node, float):
            new_val = st.number_input("Value", value=node, format="%.6f", key="raw_float")
            set_node(edited, tokens, float(new_val))

        elif isinstance(node, str):
            if len(node) > 140 or "\n" in node:
                new_val = st.text_area("Value", value=node, height=160, key="raw_str")
            else:
                new_val = st.text_input("Value", value=node, key="raw_str")
            set_node(edited, tokens, new_val)

        elif isinstance(node, list):
            st.caption("One YAML value per item.")
            for i, item in enumerate(node):
                raw = st.text_area(
                    f"Item {i + 1}",
                    value=yaml.safe_dump(item, allow_unicode=True, sort_keys=False).strip(),
                    height=80,
                    key=f"raw_list_{selected_path}_{i}",
                )
                try:
                    node[i] = yaml.safe_load(raw)
                except Exception:
                    st.warning(f"Invalid YAML at item {i + 1}.")
            add_raw = st.text_area("Add item (YAML)", value="", height=60, key="raw_list_add")
            if st.button("Add item", key="raw_add_btn"):
                if add_raw.strip():
                    try:
                        node.append(yaml.safe_load(add_raw))
                    except Exception:
                        st.warning("Invalid YAML.")
            set_node(edited, tokens, node)

        elif isinstance(node, dict):
            keys = list(node.keys())
            if keys:
                pick = st.selectbox("Select key", keys, key="raw_dict_key")
                raw = st.text_area(
                    "Value (YAML)",
                    value=yaml.safe_dump(node[pick], allow_unicode=True, sort_keys=False).strip(),
                    height=120,
                    key="raw_dict_val",
                )
                try:
                    node[pick] = yaml.safe_load(raw)
                except Exception:
                    st.warning("Invalid YAML.")
            nk = st.text_input("New key", key="raw_dict_newk")
            nv = st.text_area("New value (YAML)", height=70, key="raw_dict_newv")
            if st.button("Add key", key="raw_dict_addbtn"):
                if nk.strip():
                    try:
                        node[nk] = yaml.safe_load(nv) if nv.strip() else None
                    except Exception:
                        st.warning("Invalid YAML.")
            set_node(edited, tokens, node)

        else:
            raw = st.text_area(
                "Raw YAML",
                value=yaml.safe_dump(node, allow_unicode=True, sort_keys=False),
                height=160,
                key="raw_other",
            )
            try:
                set_node(edited, tokens, yaml.safe_load(raw))
            except Exception:
                st.warning("Invalid YAML.")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save", key="raw_save"):
                save_yaml(config_path, edited)
                st.success("Saved.")
        with c2:
            if st.button("Save + snapshot", key="raw_snap"):
                save_yaml(config_path, edited)
                ctx = type("C", (), {"snapshot_dir": snapshot_dir})()
                snap, _ = snapshot_yaml(ctx, config_path, edited)
                st.success(f"Saved. Snapshot: {snap.name}")
