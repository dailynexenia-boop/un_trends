# -*- coding: utf-8 -*-
"""
Block 4.2 — LLM Orchestrator

Responsibilities:
- Read canonical entries
- Read Block 4.2 projection policy from config
- Call LLM to project arguments
- Return raw, traceable projections

NO analytics.
NO aggregation.
NO thresholds.
"""

from typing import List, Dict, Any
import json
import os
from openai import OpenAI

from analysis.config_loader import Block4Config

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _get_api_key() -> str:
    # Streamlit Cloud secrets take priority, then environment
    try:
        import streamlit as st
        key = st.secrets.get("OPENAI_API_KEY")
        if key:
            return key
    except Exception:
        pass
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found")
    return key

# --------------------------------------------------
# LLM CLIENT (INSTRUMENT ONLY)
# --------------------------------------------------

def _get_client() -> OpenAI:
    return OpenAI(api_key=_get_api_key())

# --------------------------------------------------
# PROMPT BUILDER (INTENTION-DRIVEN)
# --------------------------------------------------

def build_prompt(
    text: str,
    argument_keys: List[str],
    policy: Dict[str, Any],
) -> str:
    """
    Build LLM prompt strictly from config.
    """
    instruction = policy.get("instruction", "").strip()

    return f"""
{instruction}

Choose ONLY from the following argument keys:

{json.dumps(argument_keys, indent=2)}

If none apply, return [].

Text:
{text}
""".strip()


# --------------------------------------------------
# CORE ORCHESTRATION
# --------------------------------------------------

def run_argument_projection(
    entries: List[Dict[str, Any]],
    cfg: Block4Config,
    argument_set: str,
) -> List[Dict[str, Any]]:
    """
    Project canonical entries onto an argumentative space.

    Returns:
    [
      {
        "entry_id": str,
        "arguments": [str, ...]
      }
    ]
    """

    block_cfg = cfg.block4_2

    argument_sets = block_cfg.get("argument_sets", {})
    policy = block_cfg.get("projection_policy", {})

    if argument_set not in argument_sets:
        raise ValueError(f"Unknown argument set: {argument_set}")

    arguments_cfg = argument_sets[argument_set]["arguments"]
    argument_keys = list(arguments_cfg.keys())

    client = _get_client()
    projections = []

    for e in entries:
        entry_id = e.get("entry_id")
        text = (e.get("signals_text") or "").strip()

        if not entry_id or not text:
            continue

        prompt = build_prompt(
            text=text,
            argument_keys=argument_keys,
            policy=policy,
        )

        response = client.chat.completions.create(
            model=policy.get("model", "gpt-4.1"),
            messages=[{"role": "user", "content": prompt}],
            temperature=policy.get("temperature", 0),
        )

        try:
            args = json.loads(response.choices[0].message.content)
            if not isinstance(args, list):
                args = []
        except Exception:
            args = []

        projections.append({
            "entry_id": entry_id,
            "arguments": args,
        })

    return projections
