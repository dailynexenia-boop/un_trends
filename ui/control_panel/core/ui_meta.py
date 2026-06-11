from __future__ import annotations
from typing import Any, Dict, List
from pathlib import Path

from ui.control_panel.core.store import load_yaml



def load_ui_descriptions(path: Path) -> Dict[str, Any]:
    return load_yaml(path) or {}


def lookup_meta(ui_desc: Dict[str, Any], filename: str, path_tokens: List[str]) -> Dict[str, Any]:
    """
    ui_descriptions.yaml is expected to be keyed by filename, then nested keys.
    Each node can contain "_meta".
    """
    node: Any = ui_desc.get(filename, {})
    for tok in path_tokens:
        if not isinstance(node, dict):
            return {}
        node = node.get(tok, {})

    if isinstance(node, dict) and "_meta" in node:
        return node.get("_meta") or {}
    return node if isinstance(node, dict) else {}
