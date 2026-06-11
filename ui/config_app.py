import streamlit as st
import yaml
from pathlib import Path
from copy import deepcopy
import difflib
import subprocess
import hashlib
from datetime import datetime
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
SNAPSHOT_DIR = CONFIG_DIR / "_snapshots"
UI_DESC = CONFIG_DIR / "ui_descriptions.yaml"

LAYERS = {
    "Analysis Logic": [CONFIG_DIR / "micro_analysis.yaml"],
    "Signal Detection": [
        CONFIG_DIR / "initiative_terms.yaml",
        CONFIG_DIR / "mechanism_terms.yaml",
        CONFIG_DIR / "delegitimization_terms.yaml",
    ],
    "Strategy & Thresholds": [CONFIG_DIR / "block4.yaml"],
    "LLM & Projections": [CONFIG_DIR / "block4.yaml"],  # block4_2 inside
    "Registers": [
        CONFIG_DIR / "countries.yaml",
        CONFIG_DIR / "institutions.yaml",
        CONFIG_DIR / "alignment_groups.yaml",
        CONFIG_DIR / "narrative_codes.yaml",
        CONFIG_DIR / "topic_position_registers.yaml",
    ],
    "Recompute & Status": [],
}

# --------------------------
# Helpers
# --------------------------
def load_yaml(path: Path):
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def save_yaml(path: Path, data):
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

def md5_text(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:10]

def get_node(data, path_tokens):
    node = data
    for t in path_tokens:
        if isinstance(node, dict):
            node = node.get(t)
        elif isinstance(node, list):
            node = node[int(t)]
        else:
            return None
    return node

def set_node(data, path_tokens, value):
    node = data
    for t in path_tokens[:-1]:
        node = node[t] if isinstance(node, dict) else node[int(t)]
    last = path_tokens[-1]
    if isinstance(node, dict):
        node[last] = value
    else:
        node[int(last)] = value

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

def load_ui_desc():
    return load_yaml(UI_DESC)

def lookup_meta(ui_desc, filename, path_str):
    # ui_descriptions.yaml is keyed by filename, then keys
    node = ui_desc.get(filename, {})
    for tok in path_str.split("."):
        if not isinstance(node, dict):
            return {}
        node = node.get(tok, {})
    if isinstance(node, dict) and "_meta" in node:
        return node.get("_meta") or {}
    return node if isinstance(node, dict) else {}

def snapshot_file(config_path: Path, data):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    h = md5_text(content)
    folder = SNAPSHOT_DIR / config_path.stem
    folder.mkdir(parents=True, exist_ok=True)
    snap = folder / f"{stamp}__{h}.yaml"
    meta = folder / f"{stamp}__{h}.meta.json"
    snap.write_text(content, encoding="utf-8")
    meta.write_text(json.dumps({"source": str(config_path), "stamp": stamp, "hash": h}, indent=2), encoding="utf-8")
    return snap

def run_cmd(cmd):
    p = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")

# --------------------------
# Page layout
# --------------------------
st.set_page_config(page_title="Configuration", layout="wide")

# Top header
st.title("Configuration")
st.caption("Exhaustive configuration editor with inline explanations. Single, consistent workflow: select → inspect → edit → save → recompute.")

ui_desc = load_ui_desc()

# Sidebar: layer selection
layer = st.sidebar.selectbox("Layer", list(LAYERS.keys()))
files = LAYERS[layer]

if layer == "Recompute & Status":
    st.subheader("Recompute & Status")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Recompute discursive analysis (global)"):
            code, out = run_cmd(["python", "analysis/recompute_canonical.py", "--all"])
            st.write(out)
    with col2:
        if st.button("Recompute discursive analysis (new only)"):
            code, out = run_cmd(["python", "analysis/recompute_canonical.py"])
            st.write(out)
    st.stop()

# If layer maps to multiple files, user selects within layer
selected_file = st.sidebar.selectbox("Configuration file", [p.name for p in files])
config_path = CONFIG_DIR / selected_file

original = load_yaml(config_path)
edited = deepcopy(original)

# Main: 2 columns (center + side peek)
center, side = st.columns([1.35, 0.65], gap="large")

with center:
    st.subheader(f"{layer} · {selected_file}")

    # Search + path picker
    all_paths = list_paths(original)
    q = st.text_input("Search key paths", placeholder="Type to search (e.g., thresholds, temperature, watch_flag)")
    filtered = [p for p in all_paths if q.lower() in p.lower()] if q else all_paths[:300]

    selected_path = st.selectbox("Select a parameter path", filtered, index=0 if filtered else 0)

    # Show a compact preview of the selected node
    node = get_node(edited, selected_path.split("."))
    st.markdown("Preview")
    st.code(yaml.safe_dump(node, allow_unicode=True, sort_keys=False), language="yaml")

    # Preview tools moved behind expanders
    with st.expander("Show diff and validation", expanded=False):
        new_text = yaml.safe_dump(edited, allow_unicode=True, sort_keys=False)
        old_text = yaml.safe_dump(original, allow_unicode=True, sort_keys=False)
        diff = "\n".join(difflib.unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm=""))
        st.code(diff if diff.strip() else "No changes.", language="diff")

with side:
    st.subheader("Details")

    # Meta from ui_descriptions
    meta = lookup_meta(ui_desc, selected_file, selected_path)
    label = meta.get("label") or selected_path.split(".")[-1]
    st.markdown(f"**{label}**")
    if meta.get("description"):
        st.caption(meta["description"])
    if meta.get("unit"):
        st.caption(f"Unit: {meta['unit']}")
    if meta.get("increase_effect"):
        st.caption(f"If increased: {meta['increase_effect']}")
    if meta.get("decrease_effect"):
        st.caption(f"If decreased: {meta['decrease_effect']}")

    # Edit widget depending on type
    current = get_node(edited, selected_path.split("."))

    if isinstance(current, bool):
        new_val = st.checkbox("Value", value=current)
        set_node(edited, selected_path.split("."), new_val)

    elif isinstance(current, int):
        new_val = st.number_input("Value", value=current, step=1, format="%d")
        set_node(edited, selected_path.split("."), int(new_val))

    elif isinstance(current, float):
        new_val = st.number_input("Value", value=current, format="%.6f")
        set_node(edited, selected_path.split("."), float(new_val))

    elif isinstance(current, str):
        if len(current) > 140 or "\n" in current:
            new_val = st.text_area("Value", value=current, height=140)
        else:
            new_val = st.text_input("Value", value=current)
        set_node(edited, selected_path.split("."), new_val)

    elif isinstance(current, list):
        st.caption("List editor. One YAML value per item.")
        for i, item in enumerate(current):
            raw = st.text_area(f"Item {i+1}", value=yaml.safe_dump(item, allow_unicode=True, sort_keys=False).strip(), height=90, key=f"item_{selected_path}_{i}")
            try:
                current[i] = yaml.safe_load(raw)
            except Exception:
                st.warning(f"Invalid YAML at item {i+1}; keeping previous value.")
        add_raw = st.text_area("Add item (YAML)", value="", height=70)
        if st.button("Add item"):
            if add_raw.strip():
                current.append(yaml.safe_load(add_raw))
        set_node(edited, selected_path.split("."), current)

    elif isinstance(current, dict):
        st.caption("Dictionary editor. Add or edit keys.")
        # Show keys as a small table-like editor
        keys = list(current.keys())
        pick_key = st.selectbox("Select key", keys) if keys else None
        if pick_key:
            raw = st.text_area("Selected key value (YAML)", value=yaml.safe_dump(current[pick_key], allow_unicode=True, sort_keys=False).strip(), height=120)
            try:
                current[pick_key] = yaml.safe_load(raw)
            except Exception:
                st.warning("Invalid YAML; not applied.")
        st.markdown("Add new key")
        nk = st.text_input("New key name")
        nv = st.text_area("New value (YAML)", height=80)
        if st.button("Add key"):
            if nk.strip():
                current[nk] = yaml.safe_load(nv) if nv.strip() else None
        set_node(edited, selected_path.split("."), current)

    else:
        st.caption("Unsupported type. Editable as raw YAML.")
        raw = st.text_area("Raw YAML", value=yaml.safe_dump(current, allow_unicode=True, sort_keys=False), height=160)
        set_node(edited, selected_path.split("."), yaml.safe_load(raw))

    st.markdown("---")

    # Save / snapshot / recompute with guard rails
    save_col1, save_col2 = st.columns(2)
    with save_col1:
        if st.button("Save"):
            save_yaml(config_path, edited)
            st.success("Saved to config.")
    with save_col2:
        if st.button("Save snapshot"):
            snap = snapshot_file(config_path, edited)
            st.success(f"Snapshot stored: {snap.name}")

    st.markdown("Recompute")
    auto_snapshot = st.checkbox("Create snapshot before recompute", value=True)

    def before_recompute():
        if auto_snapshot:
            snapshot_file(config_path, edited)
        save_yaml(config_path, edited)

    if st.button("Recompute discursive analysis (global)"):
        before_recompute()
        code, out = run_cmd(["python", "analysis/recompute_canonical.py", "--all"])
        st.code(out or "Done.", language="text")

    if st.button("Recompute strategy"):
        before_recompute()
        code, out = run_cmd(["python", "analysis/block4/run_block4.py"])
        st.code(out or "Done.", language="text")

    if st.button("Recompute LLM projections"):
        before_recompute()
        code, out = run_cmd(["python", "analysis/block4_2_llm.py"])
        st.code(out or "Done.", language="text")
