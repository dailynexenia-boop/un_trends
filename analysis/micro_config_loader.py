# analysis/micro_config_loader.py

import yaml
import warnings
from pathlib import Path
from typing import Dict, Any


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
MICRO_CONFIG_PATH = CONFIG_DIR / "micro_analysis.yaml"


# ==================================================
# ERRORS
# ==================================================

class MicroConfigError(Exception):
    """
    Raised when micro_analysis config is unusable.
    These errors MUST block execution.
    """
    pass


# ==================================================
# LOADER
# ==================================================

def load_micro_analysis_config(strict: bool = False) -> Dict[str, Any]:
    """
    Load micro_analysis.yaml with controlled validation.

    strict=False  → UI / exploration mode
    strict=True   → batch / production mode

    Blocking (always):
      - missing file
      - unreadable YAML
      - missing root key 'micro_analysis'

    Blocking only if strict=True:
      - invalid core section types

    Non-blocking (warnings):
      - missing optional sections
      - empty mappings / lists
      - incomplete triggers
    """

    # ------------------------------
    # HARD BLOCKERS (ALWAYS)
    # ------------------------------

    if not MICRO_CONFIG_PATH.exists():
        raise MicroConfigError(
            f"Missing micro_analysis config file: {MICRO_CONFIG_PATH}"
        )

    try:
        with open(MICRO_CONFIG_PATH, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except Exception as e:
        raise MicroConfigError(
            f"Unable to load micro_analysis.yaml: {e}"
        )

    if not isinstance(raw, dict):
        raise MicroConfigError(
            "Invalid micro_analysis.yaml: root must be a mapping"
        )

    if "micro_analysis" not in raw:
        raise MicroConfigError(
            "Root key 'micro_analysis' missing in micro_analysis.yaml"
        )

    cfg = raw["micro_analysis"]

    if not isinstance(cfg, dict):
        raise MicroConfigError(
            "'micro_analysis' must be a mapping"
        )

    # ------------------------------
    # CORE SECTIONS (STRUCTURAL)
    # ------------------------------

    _ensure_section(cfg, "topics", strict)
    _ensure_section(cfg, "signal_structure", strict)
    _ensure_section(cfg, "discursive_gestures", strict)
    _ensure_section(cfg, "diplomatic_posture", strict)
    _ensure_section(cfg, "explicitness", strict)
    _ensure_section(cfg, "risk", strict)
    _ensure_section(cfg, "diplomatic_acts", strict)
    _ensure_section(cfg, "watch_flag", strict)

    # ------------------------------
    # TYPE GUARDS (STRICT MODE)
    # ------------------------------

    if strict:
        _ensure_dict(cfg.get("topics"), "topics")
        _ensure_dict(cfg.get("signal_structure"), "signal_structure")
        _ensure_dict(cfg.get("discursive_gestures"), "discursive_gestures")
        _ensure_dict(cfg.get("diplomatic_posture"), "diplomatic_posture")
        _ensure_dict(cfg.get("explicitness"), "explicitness")
        _ensure_dict(cfg.get("risk"), "risk")
        _ensure_dict(cfg.get("diplomatic_acts"), "diplomatic_acts")
        _ensure_dict(cfg.get("watch_flag"), "watch_flag")

    # ------------------------------
    # SAFE DEFAULTS (NON-DOCTRINAL)
    # ------------------------------

    cfg.setdefault("topics", {})
    cfg.setdefault("signal_structure", {})
    cfg.setdefault("discursive_gestures", {})
    cfg.setdefault("diplomatic_posture", {})
    cfg.setdefault("explicitness", {})
    cfg.setdefault("risk", {})
    cfg.setdefault("diplomatic_acts", {"enabled": False, "acts": {}})
    cfg.setdefault("watch_flag", {"enabled": False, "triggers": {}})

    return cfg


# ==================================================
# INTERNAL HELPERS
# ==================================================

def _ensure_section(cfg: Dict[str, Any], key: str, strict: bool):
    if key not in cfg:
        msg = f"Missing section '{key}' in micro_analysis config"
        if strict:
            raise MicroConfigError(msg)
        warnings.warn(msg)
        cfg[key] = {}


def _ensure_dict(value: Any, path: str):
    if not isinstance(value, dict):
        raise MicroConfigError(
            f"Invalid type for '{path}': expected mapping"
        )
