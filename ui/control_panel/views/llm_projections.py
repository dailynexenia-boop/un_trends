import streamlit as st
from pathlib import Path
from typing import Dict, Any

from ui.control_panel.core.store import load_yaml, save_yaml
from ui.control_panel.core.components import section


def render(
    config_dir: Path,
    ui_desc: Dict[str, Any],
    project_root: Path,
    snapshot_dir: Path,
):
    st.subheader("LLM & Projections")
    st.caption(
        "Controls how language models are used to project arguments. "
        "This layer does not affect analytical logic or canonical data."
    )

    cfg_path = config_dir / "block4.yaml"
    cfg = load_yaml(cfg_path)

    block4_2 = cfg.setdefault("block4_2", {})
    policy = block4_2.setdefault("projection_policy", {})

    # =====================================================
    # INFO
    # =====================================================

    st.info(
        "This page controls the **LLM projection layer only**.\n\n"
        "- Argument sets are defined in **Analytical Core (Block 4.2)**\n"
        "- This does not change analytical results\n"
        "- Changes take effect after recomputation"
    )

    # =====================================================
    # MODEL BEHAVIOUR
    # =====================================================

    section(
        "Model behaviour",
        "Controls which model is used and how deterministic its output is."
    )

    model = st.text_input(
        "LLM model",
        value=policy.get("model", "gpt-4.1"),
        help="Model identifier passed to the OpenAI client.",
    )

    temperature = st.number_input(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        step=0.1,
        value=float(policy.get("temperature", 0)),
        help="0 = fully deterministic, higher values allow more variation.",
    )

    # =====================================================
    # PROMPT (FULL WIDTH, READABLE)
    # =====================================================

    section(
        "Projection instruction",
        "This instruction is sent to the language model before the argument list and input text."
    )

    instruction = st.text_area(
        "Instruction",
        value=policy.get("instruction", ""),
        height=260,
        help=(
            "This prompt defines how the model selects arguments.\n"
            "It should clearly specify the expected output format and constraints."
        ),
    )

    # =====================================================
    # OUTPUT CONSTRAINTS
    # =====================================================

    section(
        "Output constraints",
        "Controls how strictly the model must follow the provided argument list."
    )

    strict_mode = st.checkbox(
        "Strict mode (reject invalid outputs)",
        value=bool(policy.get("strict_mode", True)),
        help=(
            "If enabled, the model must return only argument keys "
            "from the provided list. Invalid outputs are discarded."
        ),
    )

    # =====================================================
    # SAVE / SAFEGUARD
    # =====================================================

    st.divider()

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("💾 Save configuration"):
            policy["model"] = model
            policy["temperature"] = temperature
            policy["instruction"] = instruction
            policy["strict_mode"] = strict_mode

            save_yaml(cfg_path, cfg)

            st.success("LLM projection configuration saved.")

    with col2:
        st.caption(
            "This writes the projection policy to `block4.yaml`. "
            "Changes take effect after recomputation."
        )
