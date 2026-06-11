# -*- coding: utf-8 -*-
"""
Analytical Core — Control Panel (FINAL, REGISTER-READY)

- Architecture preserved
- Same UI logic as Block 4 everywhere
- Registers: editable + addable
- Entry points: editable + addable
- Argument sets: editable + parametrable
- Thresholds explained (dummy-proof)
"""

from pathlib import Path
from datetime import datetime
import json
import shutil
import yaml
import ast
import re
import streamlit as st

# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"
BLOCK4_PATH = CONFIG_DIR / "block4.yaml"
CANONICAL_PATH = PROJECT_ROOT / "canonical" / "canonical.jsonl"

# ==================================================
# YAML HELPERS
# ==================================================

def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_yaml_with_backup(path: Path, content: dict):
    history_dir = path.parent / "_history"
    history_dir.mkdir(exist_ok=True)

    if path.exists():
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        shutil.copy2(path, history_dir / f"{path.name}.{ts}.bak")

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(content, f, allow_unicode=True, sort_keys=False)

# ==================================================
# UI NORMALIZATION (LEGACY-SAFE)
# ==================================================

def ui_normalize(value, default=None):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return default if default is not None else {}

# ==================================================
# CANONICAL KEYWORDS
# ==================================================

def load_canonical_keywords() -> list[str]:
    keywords = set()
    if not CANONICAL_PATH.exists():
        return []
    with open(CANONICAL_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                for kw in entry.get("keywords", []):
                    if isinstance(kw, str):
                        keywords.add(kw.lower())
            except Exception:
                continue
    return sorted(keywords)

# ==================================================
# GENERIC UI HELPERS
# ==================================================

def edit_list(label: str, values: list, key: str) -> list:
    text = st.text_area(
        label,
        value="\n".join(values or []),
        height=120,
        key=key,
    )
    return [v.strip() for v in text.splitlines() if v.strip()]

# ==================================================
# POLITICAL COST — HUMAN UI
# ==================================================

def to_safe_regex(term: str) -> str:
    return rf"\b{re.escape(term.strip())}\b"

def split_cost_patterns(patterns):
    simple, advanced = [], []
    for p in patterns or []:
        if isinstance(p, str) and p.startswith(r"\b") and p.endswith(r"\b"):
            simple.append(p[2:-2].replace("\\", ""))
        else:
            advanced.append(p)
    return simple, advanced

def edit_political_cost(cost_cfg: dict) -> dict:
    st.info(
        "Political cost estimates political sensitivity.\n"
        "High / Medium increase sensitivity; low anchors reduce it.\n"
        "Write normal words — regex is handled internally."
    )

    updated = {}

    for level in ["high", "medium"]:
        with st.expander(f"{level.title()} political sensitivity", expanded=False):
            simple, advanced = split_cost_patterns(cost_cfg.get(level, []))

            st.caption("Currently active expressions:")
            st.markdown(", ".join(simple) if simple else "_None_")

            edited = edit_list(
                "Edit expressions (one per line)",
                simple,
                f"cost_{level}",
            )

            updated[level] = [to_safe_regex(t) for t in edited if t.strip()] + advanced

    with st.expander("Low sensitivity anchors", expanded=False):
        updated["low_anchors"] = edit_list(
            "Edit low-sensitivity anchors",
            cost_cfg.get("low_anchors", []),
            "cost_low",
        )

    return updated

# ==================================================
# PAGE
# ==================================================

def render(*args, **kwargs):
    st.subheader("Analytical Core")
    st.caption("Strategic analytical doctrine — reload required after save")

    cfg = load_yaml(BLOCK4_PATH)
    updated = {}

    canonical_keywords = load_canonical_keywords()
    canonical_set = set(canonical_keywords)

    # ==================================================
    # BLOCK 4 — KEYWORD AGGREGATIONS
    # ==================================================

    with st.expander("Block 4 — Keyword aggregations", expanded=True):
        b4 = cfg.get("block4", {})
        updated_aggs = {}

        for key, raw in (b4.get("keyword_aggregations") or {}).items():
            agg = ui_normalize(raw, {"label": "", "members": []})
            members = agg.get("members", [])

            valid = [m for m in members if isinstance(m, str) and m.lower() in canonical_set]
            legacy = [m for m in members if m not in valid]

            with st.expander(f"Aggregation — {key}", expanded=False):
                st.caption("Currently associated keywords:")
                st.markdown(", ".join(members) if members else "_None_")

                if legacy:
                    st.caption("⚠️ Not present in canonical keywords (kept as-is):")
                    st.markdown(", ".join(legacy))

                edited = st.multiselect(
                    "Edit canonical keywords",
                    options=canonical_keywords,
                    default=[m.lower() for m in valid],
                    key=f"agg_{key}",
                )

                updated_aggs[key] = {
                    "label": agg.get("label", ""),
                    "members": sorted(set(legacy + edited)),
                }

        updated["block4"] = {
            "keyword_aggregations": updated_aggs,
            "limits": b4.get("limits", {}),
        }

    # ==================================================
    # BLOCK 4.1 — STRATEGIC LOGIC
    # ==================================================

    with st.expander("Block 4.1 — Strategic logic", expanded=False):
        b41 = cfg.get("block4_1", {})

        # ------------------------------
        # REGISTERS (EDIT + ADD)
        # ------------------------------

        st.markdown("## Registers")
        updated_registers = {}

        for reg, terms in (b41.get("registers") or {}).items():
            terms = terms or []
            with st.expander(f"Register — {reg}", expanded=False):
                st.caption("Current terms:")
                st.markdown(", ".join(terms) if terms else "_None_")

                edited = edit_list(
                    "Edit register terms",
                    terms,
                    f"reg_{reg}",
                )

                updated_registers[reg] = edited

        # ADD NEW REGISTER (EXACTLY LIKE BLOCK 4)
        st.markdown("### Add new register")

        new_register_key = st.text_input(
            "Register key (snake_case)",
            key="new_register_key",
        )

        new_register_terms = edit_list(
            "Initial terms for this register",
            [],
            "new_register_terms",
        )

        if new_register_key:
            updated_registers[new_register_key] = new_register_terms

        # ------------------------------
        # POLITICAL COST
        # ------------------------------

        st.divider()
        updated_cost = edit_political_cost(
            ui_normalize(b41.get("political_cost"), {})
        )

        # ------------------------------
        # ENTRY POINT BUCKETS (EDIT + ADD)
        # ------------------------------

        st.divider()
        st.markdown("## Entry point buckets")
        updated_buckets = {}

        for bucket, terms in (b41.get("entry_point_buckets") or {}).items():
            terms = terms or []
            with st.expander(f"Bucket — {bucket}", expanded=False):
                st.caption("Current terms:")
                st.markdown(", ".join(terms) if terms else "_None_")

                edited = edit_list(
                    "Edit bucket terms",
                    terms,
                    f"bucket_{bucket}",
                )

                updated_buckets[bucket] = edited

        st.markdown("### Add new entry point")

        new_bucket_key = st.text_input(
            "Entry point key (snake_case)",
            key="new_entry_point_key",
        )

        new_bucket_terms = edit_list(
            "Initial terms for this entry point",
            [],
            "new_entry_point_terms",
        )

        if new_bucket_key:
            updated_buckets[new_bucket_key] = new_bucket_terms

        # ------------------------------
        # THRESHOLDS (EXPLAINED)
        # ------------------------------

        st.divider()
        st.markdown("## Strategic thresholds")
        st.info(
            "Thresholds define when a topic becomes analytically significant.\n"
            "Higher values = stricter classification."
        )

        thresholds = ui_normalize(b41.get("thresholds"), {})

        inst = ui_normalize(
            thresholds.get("perception", {}).get("institutionalised", {}),
            {"min_entries": 0, "min_countries": 0},
        )

        min_entries = st.number_input(
            "Minimum number of statements",
            value=int(inst["min_entries"]),
            min_value=0,
        )

        min_countries = st.number_input(
            "Minimum number of countries",
            value=int(inst["min_countries"]),
            min_value=0,
        )

        bridge = ui_normalize(thresholds.get("bridge_score"), {})
        weights = ui_normalize(
            bridge.get("posture_weights"),
            {"normative": 0, "defensive": 0, "accusatory": 0},
        )

        updated_weights = {
            k: st.number_input(f"Weight for {k} posture", value=int(v))
            for k, v in weights.items()
        }

        topic_bonus = st.number_input(
            "Topic convergence bonus",
            value=int(bridge.get("topic_count_bonus", 0)),
        )

        updated["block4_1"] = {
            "registers": updated_registers,
            "political_cost": updated_cost,
            "entry_point_buckets": updated_buckets,
            "preferred_entry_point_order": edit_list(
                "Preferred entry point order",
                b41.get("preferred_entry_point_order", []),
                "entry_order",
            ),
            "thresholds": {
                "perception": {
                    "institutionalised": {
                        "min_entries": min_entries,
                        "min_countries": min_countries,
                    }
                },
                "bridge_score": {
                    "posture_weights": updated_weights,
                    "topic_count_bonus": topic_bonus,
                },
            },
        }

    # ==================================================
    # BLOCK 4.2 — ARGUMENTATIVE OVERLAY
    # ==================================================

    with st.expander("Block 4.2 — Argumentative overlay", expanded=False):
        b42 = cfg.get("block4_2", {})
        updated_b42 = {}

        st.info(
            "This block controls how arguments are projected and classified.\n"
            "Only predefined arguments are allowed in strict mode."
        )

        proj = ui_normalize(b42.get("projection_policy"), {})

        updated_b42["projection_policy"] = {
            "instruction": st.text_area(
                "Projection instruction",
                proj.get("instruction", ""),
                height=120,
            ),
            "strict_mode": st.toggle(
                "Strict mode",
                str(proj.get("strict_mode")).lower() == "true",
            ),
            "output_format": proj.get("output_format", "json_list"),
        }

        # Resonance thresholds
        res = ui_normalize(b42.get("resonance_thresholds"), {})
        updated_res = {}

        for level, cfg_r in res.items():
            cfg_r = ui_normalize(cfg_r, {})
            with st.expander(level.replace("_", " ").title(), expanded=False):
                updated_res[level] = {
                    k: st.number_input(
                        k.replace("_", " ").title(),
                        value=int(v),
                        min_value=0,
                    )
                    for k, v in cfg_r.items()
                }

        updated_b42["resonance_thresholds"] = updated_res

        # Argument sets (EDIT + ADD ARGUMENTS)
        updated_sets = {}

        for set_key, raw_set in (b42.get("argument_sets") or {}).items():
            set_cfg = ui_normalize(raw_set, {"description": "", "arguments": {}})
            args = set_cfg.get("arguments", {})

            with st.expander(f"Argument set — {set_key}", expanded=False):
                desc = st.text_area(
                    "Description",
                    set_cfg.get("description", ""),
                    key=f"arg_desc_{set_key}",
                    height=80,
                )

                updated_args = {}

                for arg_key, arg_cfg in args.items():
                    arg_cfg = ui_normalize(arg_cfg, {"label": "", "category": ""})

                    st.markdown(f"**Argument — `{arg_key}`**")

                    label = st.text_input(
                        "Label",
                        arg_cfg.get("label", ""),
                        key=f"{set_key}_{arg_key}_label",
                    )

                    category = st.text_input(
                        "Category",
                        arg_cfg.get("category", ""),
                        key=f"{set_key}_{arg_key}_category",
                    )

                    delete = st.checkbox(
                        f"Delete argument `{arg_key}`",
                        key=f"delete_{set_key}_{arg_key}",
                    )

                    if not delete:
                        updated_args[arg_key] = {
                            "label": label,
                            "category": category,
                        }

                    st.divider()

                st.markdown("### Add new argument")

                new_arg_key = st.text_input(
                    "Argument key (snake_case)",
                    key=f"new_arg_key_{set_key}",
                )

                new_arg_label = st.text_input(
                    "Label",
                    key=f"new_arg_label_{set_key}",
                )

                new_arg_category = st.text_input(
                    "Category",
                    key=f"new_arg_category_{set_key}",
                )

                if new_arg_key:
                    updated_args[new_arg_key] = {
                        "label": new_arg_label,
                        "category": new_arg_category,
                    }

                updated_sets[set_key] = {
                    "description": desc,
                    "arguments": updated_args,
                }

        updated_b42["argument_sets"] = updated_sets
        updated["block4_2"] = updated_b42

    # ==================================================
    # SAVE
    # ==================================================

    st.divider()
    if st.button("💾 Save analytical configuration"):
        # Merge into full file — block4.yaml contains other keys (block2_5, block3, etc.)
        # that are owned by other views and must not be overwritten.
        full = load_yaml(BLOCK4_PATH)
        full.update(updated)
        save_yaml_with_backup(BLOCK4_PATH, full)
        st.success("Configuration saved successfully. Reload to apply.")
