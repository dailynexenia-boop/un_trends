# -*- coding: utf-8 -*-
"""
UN-LOG — Control Interface (FINAL, ROBUST)

- YAML-backed
- Recompute-safe
- Quick Config: Registers / Keywords / Micro / Argumentation
- Thresholds: exhaustive auto-discovery across Block4 + Micro + Dashboard (+ Block5 if present)
- Uses ui_descriptions.yaml when available, with safe fallback explanations
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import yaml
import streamlit as st
import re
from typing import Any, Dict, List, Tuple, Optional


# ==================================================
# PATHS
# ==================================================
ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config"

FILES = {
    "countries": CONFIG / "countries.yaml",
    "alignment_groups": CONFIG / "alignment_groups.yaml",
    "institutions": CONFIG / "institutions.yaml",
    "initiative_terms": CONFIG / "initiative_terms.yaml",
    "mechanism_terms": CONFIG / "mechanism_terms.yaml",
    "delegitimization_terms": CONFIG / "delegitimization_terms.yaml",
    "micro_analysis": CONFIG / "micro_analysis.yaml",
    "block4": CONFIG / "block4.yaml",
    "dashboard": CONFIG / "dashboard_alerts.yaml",
    "block5": CONFIG / "block5.yaml",  # optional; safe if missing
    "ui_desc": CONFIG / "ui_descriptions.yaml",
}


# ==================================================
# YAML HELPERS
# ==================================================
def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        st.error(f"Failed to parse YAML: {path.name}\n{e}")
        return {}

def save_yaml(path: Path, data: dict) -> None:
    try:
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    except Exception as e:
        st.error(f"Failed to write YAML: {path.name}\n{e}")

def run_cmd(cmd: List[str]) -> None:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    st.code(out, language="text")


# ==================================================
# SAFE ACCESS / PATH OPS
# ==================================================
def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def ensure_dict(d: Any) -> dict:
    return d if isinstance(d, dict) else {}

def ensure_list(x: Any) -> list:
    return x if isinstance(x, list) else []

def get_in(d: Any, path: List[str], default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict):
            cur = cur.get(p, default)
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except Exception:
                return default
        else:
            return default
    return cur

def set_in(d: Any, path: List[str], value: Any) -> None:
    cur = d
    for p in path[:-1]:
        if isinstance(cur, dict):
            if p not in cur or not isinstance(cur[p], (dict, list)):
                cur[p] = {}
            cur = cur[p]
        elif isinstance(cur, list):
            idx = int(p)
            while len(cur) <= idx:
                cur.append({})
            if not isinstance(cur[idx], (dict, list)):
                cur[idx] = {}
            cur = cur[idx]
        else:
            raise ValueError("Invalid structure for set_in")
    last = path[-1]
    if isinstance(cur, dict):
        cur[last] = value
    elif isinstance(cur, list):
        idx = int(last)
        while len(cur) <= idx:
            cur.append(None)
        cur[idx] = value


# ==================================================
# UI DESCRIPTIONS (OPTIONAL)
# ==================================================
def ui_meta_lookup(ui_desc: dict, dotted_path: str) -> dict:
    """
    Looks up a dotted path in ui_descriptions.yaml and returns _meta if present.
    Works even if ui_descriptions.yaml is only partially populated.
    """
    if not ui_desc or not isinstance(ui_desc, dict):
        return {}
    node = ui_desc
    for part in dotted_path.split("."):
        if not isinstance(node, dict):
            return {}
        node = node.get(part)
        if node is None:
            return {}
    if isinstance(node, dict) and "_meta" in node and isinstance(node["_meta"], dict):
        return node["_meta"]
    return {}


# ==================================================
# THRESHOLD DISCOVERY (EXHAUSTIVE)
# ==================================================
THRESHOLD_HINTS = (
    "threshold", "thresholds", "resonance",
    "min_", "max_", "limit", "cap",
    "window", "half", "decay",
    "count", "hits",
    "bonus", "weight", "ratio", "score",
    "burst", "spike", "watch", "risk"
)

def looks_like_threshold_key(k: str) -> bool:
    k = str(k).lower()
    return any(h in k for h in THRESHOLD_HINTS)

def path_has_threshold_hint(path: List[str]) -> bool:
    joined = ".".join(map(str, path)).lower()
    return any(h in joined for h in ("threshold", "thresholds", "resonance", "alerts", "watch", "risk", "burst", "spike", "decay"))

def iter_numeric_leaves(obj: Any, prefix: Optional[List[str]] = None):
    """
    Yield (path, value) for numeric leaves.
    """
    if prefix is None:
        prefix = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_numeric_leaves(v, prefix + [str(k)])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_numeric_leaves(v, prefix + [str(i)])
    else:
        if is_number(obj):
            yield prefix, obj

def nice_label(path: List[str]) -> str:
    k = str(path[-1]).replace("_", " ").strip()
    k = re.sub(r"\s+", " ", k)
    return k[:1].upper() + k[1:]


def default_doctrine_for(path: List[str]) -> str:
    k = str(path[-1]).lower()
    if "min" in k:
        return ("Minimum requirement. Increasing it makes the system stricter "
                "and fewer cases will qualify.")
    if "max" in k:
        return ("Maximum limit. Decreasing it makes the system stricter "
                "and fewer items will be allowed.")
    if "window" in k:
        return ("Time window. Larger window = more stable but less reactive; "
                "smaller window = more reactive but noisier.")
    if "decay" in k or "half" in k:
        return ("Decay parameter. Larger values make signals persist longer; "
                "smaller values make signals fade faster.")
    if "count" in k or "hits" in k:
        return ("Count threshold. Higher values require repeated signals before triggering.")
    if "weight" in k:
        return ("Weight factor. Higher values increase the influence of this component.")
    if "bonus" in k:
        return ("Bonus parameter. Higher bonus increases score when this condition happens.")
    return ("Threshold parameter. Higher values generally make detection stricter; "
            "lower values make it more sensitive.")


# ==================================================
# EXPLAINED CONTROL (STAGIAIRE-PROOF)
# ==================================================
def explained_numeric_control(
    title: str,
    dotted_path: str,
    current: float,
    is_int: bool,
    min_v: float,
    max_v: float,
    doctrine: str,
    up_effect: str,
    down_effect: str,
    example: str,
    key: str,
):
    st.subheader(title)
    st.caption(f"`{dotted_path}`")
    st.info(doctrine)

    st.markdown("**Current configuration**")
    st.metric("Current value", int(current) if is_int else float(current))

    st.markdown("**Adjust parameter**")
    if is_int:
        new_val = st.slider(
            title,
            min_value=int(min_v),
            max_value=int(max_v),
            value=int(current),
            key=key,
        )
        st.progress((new_val - int(min_v)) / max(1, (int(max_v) - int(min_v))))
    else:
        new_val = st.number_input(
            title,
            value=float(current),
            step=0.01,
            key=key,
        )

    st.markdown("**Analytical impact**")
    st.caption(f"⬆ Increasing → {up_effect}")
    st.caption(f"⬇ Decreasing → {down_effect}")

    st.markdown("**Concrete example**")
    st.caption(example)

    return new_val


# ==================================================
# STREAMLIT UI SETUP
# ==================================================
st.set_page_config(page_title="UN-LOG — Control", layout="wide")
st.title("UN-LOG — Control Interface")
st.caption("Operational configuration · YAML-backed · Recompute-safe")

page = st.sidebar.radio("Navigation", ["Quick Config", "Thresholds", "Advanced"])


# ==================================================
# PAGE — QUICK CONFIG
# ==================================================
if page == "Quick Config":
    st.header("Quick Configuration")
    tabs = st.tabs(["Registers", "Keywords & Signals", "Argumentation", "Micro Analysis"])

    # ---------------- REGISTERS ----------------
    with tabs[0]:
        st.subheader("Countries Register")

        countries = load_yaml(FILES["countries"])
        if not countries:
            st.warning("countries.yaml is empty or missing.")
            with st.expander("Debug countries.yaml"):
                st.code(yaml.safe_dump(countries, allow_unicode=True, sort_keys=False), language="yaml")
            st.stop()

        country_names = sorted(countries.keys())
        c = st.selectbox("Country", country_names)

        cfg = ensure_dict(countries.get(c, {}))

        st.markdown("### Current configuration")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Aliases**")
            st.code("\n".join(cfg.get("aliases", [])) or "_None_", language="text")
        with col2:
            st.markdown("**Regional group**")
            st.code(cfg.get("regional_group", "_undefined_"), language="text")

        st.divider()
        st.markdown("### Edit")
        new_aliases = st.text_area(
            "Aliases (one per line)",
            value="\n".join(cfg.get("aliases", [])),
            height=120,
        ).splitlines()

        new_rg = st.text_input(
            "Regional group",
            value=str(cfg.get("regional_group", "")),
        )

        if st.button("Save country configuration"):
            cfg["aliases"] = [a.strip() for a in new_aliases if a.strip()]
            cfg["regional_group"] = new_rg.strip()
            countries[c] = cfg
            save_yaml(FILES["countries"], countries)
            st.success(f"Saved: {c}")

    # ---------------- KEYWORDS ----------------
    with tabs[1]:
        st.subheader("Keywords & Signals")
        for key in ["initiative_terms", "mechanism_terms", "delegitimization_terms"]:
            data = load_yaml(FILES[key])
            title = key.replace("_", " ").title()
            st.markdown(f"### {title}")

            if not data:
                st.warning(f"{FILES[key].name} is empty.")
                st.divider()
                continue

            groups = sorted(data.keys())
            g = st.selectbox(f"{title} group", groups, key=f"group_{key}")
            terms = ensure_list(data.get(g, []))

            st.markdown("**Current terms**")
            st.code("\n".join(terms) or "_None_", language="text")

            edited = st.text_area(
                "Edit terms (one per line)",
                value="\n".join(terms),
                height=140,
                key=f"edit_{key}_{g}",
            ).splitlines()

            if st.button(f"Save group: {g}", key=f"save_{key}_{g}"):
                data[g] = [t.strip() for t in edited if t.strip()]
                save_yaml(FILES[key], data)
                st.success(f"Saved: {g}")

            st.divider()

    # ---------------- ARGUMENTATION ----------------
    with tabs[2]:
        st.subheader("Argumentation (Block 4)")
        b4 = load_yaml(FILES["block4"])
        arg_sets = ensure_dict(b4.get("argument_sets", {}))

        if not arg_sets:
            st.warning("No argument sets found in block4.yaml under key: argument_sets")
            with st.expander("Debug block4.yaml"):
                st.code(yaml.safe_dump(b4, allow_unicode=True, sort_keys=False), language="yaml")
        else:
            a = st.selectbox("Argument set", sorted(arg_sets.keys()))
            cfg = ensure_dict(arg_sets.get(a, {}))
            enabled = st.checkbox("Enabled", value=bool(cfg.get("enabled", True)))

            st.markdown("**Current**")
            st.code(cfg, language="yaml")

            if st.button("Save argument set"):
                cfg["enabled"] = enabled
                arg_sets[a] = cfg
                b4["argument_sets"] = arg_sets
                save_yaml(FILES["block4"], b4)
                st.success("Saved argument set.")

    # ---------------- MICRO ANALYSIS ----------------
    with tabs[3]:
        st.subheader("Micro Analysis (read-only here)")
        micro = load_yaml(FILES["micro_analysis"])
        st.caption("For full doctrinal editing, keep using the dedicated micro analysis editor page/app.")
        st.code(micro, language="yaml")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Recompute canonical (ALL)"):
            run_cmd(["python", "analysis/recompute_canonical.py", "--all"])
    with col2:
        if st.button("Recompute Block 4"):
            run_cmd(["python", "analysis/block4/run_block4.py"])


# ==================================================
# PAGE — THRESHOLDS (EXHAUSTIVE, SAFE)
# ==================================================
elif page == "Thresholds":
    st.header("Analytical Thresholds")
    st.caption(
        "Exhaustive threshold cockpit. This page scans real YAML configs and shows "
        "every numeric parameter that looks like a threshold/limit/cap."
    )

    ui_desc = load_yaml(FILES["ui_desc"])  # optional, may be partial

    # Load all sources (block5 optional)
    block4 = load_yaml(FILES["block4"])
    micro = load_yaml(FILES["micro_analysis"])
    dashboard = load_yaml(FILES["dashboard"])
    block5 = load_yaml(FILES["block5"]) if FILES["block5"].exists() else {}

    sources: List[Tuple[str, str, dict, Path]] = [
        ("Block 4", "block4.yaml", block4, FILES["block4"]),
        ("Micro Analysis", "micro_analysis.yaml", micro, FILES["micro_analysis"]),
        ("Dashboard", "dashboard_alerts.yaml", dashboard, FILES["dashboard"]),
    ]
    if block5:
        sources.append(("Block 5", "block5.yaml", block5, FILES["block5"]))

    # Collect candidates
    candidates: List[Tuple[str, str, dict, Path, List[str], Any]] = []
    for domain, fname, data, fpath in sources:
        for p, v in iter_numeric_leaves(data):
            # broaden detection: key hint OR path hint
            if looks_like_threshold_key(p[-1]) or path_has_threshold_hint(p):
                candidates.append((domain, fname, data, fpath, p, v))

    if not candidates:
        st.error(
            "No threshold-like numeric parameters detected. "
            "This usually means the YAML contains few numeric values or the detection hints are too strict."
        )
        with st.expander("Debug: show numeric leaves (raw)"):
            raw = []
            for domain, fname, data, fpath in sources:
                for p, v in iter_numeric_leaves(data):
                    raw.append((fname, ".".join(p), v))
            st.code("\n".join(f"{a} | {b} = {c}" for a,b,c in raw[:500]), language="text")
        st.stop()

    # Group by domain
    grouped: Dict[str, List[Tuple[str, str, dict, Path, List[str], Any]]] = {}
    for item in candidates:
        grouped.setdefault(item[0], []).append(item)

    changed_any = False

    for domain in grouped:
        items = grouped[domain]
        items.sort(key=lambda x: ".".join(x[4]))

        with st.expander(f"{domain} — {len(items)} parameters", expanded=True):
            for _, fname, data, fpath, p, v in items:
                dotted_path = ".".join(p)
                label = nice_label(p)

                # Try ui_descriptions meta
                meta = ui_meta_lookup(ui_desc, dotted_path)

                doctrine = meta.get("doctrine") or meta.get("description") or default_doctrine_for(p)
                up_effect = meta.get("increase_effect") or "The system becomes stricter (fewer detections)."
                down_effect = meta.get("decrease_effect") or "The system becomes more sensitive (more detections)."
                example = meta.get("example") or "Adjust carefully and validate by recomputing."

                # Determine ranges (safe heuristics)
                is_int = isinstance(v, int) and not isinstance(v, bool)
                cur = float(v) if isinstance(v, float) else int(v)

                # If ui meta provides min/max, use them
                min_v = meta.get("min", None)
                max_v = meta.get("max", None)

                if min_v is None:
                    min_v = 0 if is_int else 0.0

                if max_v is None:
                    if is_int:
                        max_v = max(10, min(500, int(cur) * 5 if cur > 0 else 50))
                    else:
                        max_v = max(1.0, float(cur) * 5 if cur > 0 else 10.0)

                new_val = explained_numeric_control(
                    title=meta.get("label") or label,
                    dotted_path=f"{fname}:{dotted_path}",
                    current=cur,
                    is_int=is_int,
                    min_v=min_v,
                    max_v=max_v,
                    doctrine=doctrine,
                    up_effect=up_effect,
                    down_effect=down_effect,
                    example=example,
                    key=f"thr:{fname}:{dotted_path}",
                )

                # Write back if changed
                if (is_int and int(new_val) != int(cur)) or ((not is_int) and float(new_val) != float(cur)):
                    set_in(data, p, int(new_val) if is_int else float(new_val))
                    changed_any = True

                st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Save all changes"):
            # save each loaded dict to its file
            save_yaml(FILES["block4"], block4)
            save_yaml(FILES["micro_analysis"], micro)
            save_yaml(FILES["dashboard"], dashboard)
            if block5:
                save_yaml(FILES["block5"], block5)
            st.success("Saved all threshold changes.")

    with col2:
        if st.button("🔁 Recompute canonical (ALL)"):
            run_cmd(["python", "analysis/recompute_canonical.py", "--all"])

    with col3:
        if st.button("🔁 Recompute Block 4"):
            run_cmd(["python", "analysis/block4/run_block4.py"])


# ==================================================
# PAGE — ADVANCED
# ==================================================
else:
    st.header("Advanced Configuration")
    st.warning("Use only for exhaustive / expert edits.")
    st.markdown("Launch separately:\n\n```bash\nstreamlit run config_app.py\n```")
