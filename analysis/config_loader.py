# -*- coding: utf-8 -*-
"""
Config Loader — Block 4 (FINAL)

Principles:
- ONE loader
- ONE YAML (block4.yaml)
- ONE namespace per block (block4, block4_1, block4_2, ...)
- NO business logic
- NO analytics
- Backward compatible with legacy dict access
"""

from pathlib import Path
from typing import Dict, Any
import yaml


# ==================================================
# ERRORS
# ==================================================

class Block4ConfigError(Exception):
    """Raised when block4 configuration is missing or invalid."""
    pass

# ==================================================
# CONFIG OBJECT
# ==================================================

class Block4Config:
    """
    YAML structure expected:

    {
        block2: {...},
        block4: {...},
        block4_1: {...},
        block4_2: {...},   # future
        block4_3: {...}    # future
    }
    """

    def __init__(self, raw: Dict[str, Any]):
        if not isinstance(raw, dict):
            raise Block4ConfigError("Config root must be a dict")

        self._raw = raw

        # -------------------------------
        # Namespaces (isolated per block)
        # -------------------------------

        self.block2 = raw.get("block2", {})     
        self.block4 = raw.get("block4", {})
        self.block4_1 = raw.get("block4_1", {})
        self.block2_5 = raw.get("block2_5", {})
        self.block3 = raw.get("block3", {})

        if not isinstance(self.block2, dict):
            raise Block4ConfigError("'block2' must be a dict")

        if not isinstance(self.block4, dict):
            raise Block4ConfigError("'block4' must be a dict")

        if not isinstance(self.block4_1, dict):
            raise Block4ConfigError("'block4_1' must be a dict")

        # Future-proof (no validation yet)
        self.block4_2 = raw.get("block4_2", {})
        self.block4_3 = raw.get("block4_3", {})

    # --------------------------------------------------
    # LEGACY COMPATIBILITY (DO NOT REMOVE)
    # --------------------------------------------------

    def get(self, key, default=None):
        """
        Dict-like access for legacy code.

        Example:
        cfg.get("block4", {})
        """
        return self._raw.get(key, default)

    # ==================================================
    # BLOCK 4 — OVERVIEW (LEGACY / UI)
    # ==================================================

    @property
    def block4_keyword_aggregations(self) -> Dict[str, Any]:
        """
        Block 4 subject aggregations.

        Kept for backward compatibility with existing Block 4 code.
        """
        return self.block4.get("keyword_aggregations", self.block4)

    @property
    def block4_limits(self) -> Dict[str, int]:
        """
        UI-only limits for Block 4 overview.
        """
        limits = self.block4.get("limits", {})
        return {
            "top_subjects": limits.get("top_subjects", 20),
            "top_angles": limits.get("top_angles", 5),
            "top_countries": limits.get("top_countries", 5),
        }

    # ==================================================
    # BLOCK 4.1 — STRATEGIC CORE
    # ==================================================

    @property
    def registers(self) -> Dict[str, Any]:
        return self.block4_1.get("registers", {})

    @property
    def political_cost(self) -> Dict[str, Any]:
        return self.block4_1.get("political_cost", {})

    @property
    def high_cost_patterns(self) -> list:
        return self.political_cost.get("high", [])

    @property
    def medium_cost_patterns(self) -> list:
        return self.political_cost.get("medium", [])

    @property
    def low_cost_anchors(self) -> list:
        # YAML uses "low"
        return self.political_cost.get("low", [])

    @property
    def entry_point_buckets(self) -> Dict[str, list]:
        return self.block4_1.get("entry_point_buckets", {})

    @property
    def preferred_entry_point_order(self) -> list:
        return self.block4_1.get("preferred_entry_point_order", [])

    @property
    def thresholds(self) -> Dict[str, Any]:
        return self.block4_1.get("thresholds", {})
    # ==================================================
    # BLOCK 4.2 — ARGUMENTATIVE OVERLAY
    # ==================================================

    @property
    def argument_sets(self) -> Dict[str, Any]:
        """
        Argument sets used for argumentative projection (Block 4.2).
        """
        return self.block4_2.get("argument_sets", {})

    @property
    def resonance_thresholds(self) -> Dict[str, Any]:
        """
        Thresholds used to interpret argument resonance.
        """
        return self.block4_2.get("resonance_thresholds", {})

    @property
    def projection_policy(self) -> Dict[str, Any]:
        """
        LLM projection instructions and constraints.
        """
# ==================================================
# BLOCK 3 — REGIONAL SUMMARY
# ==================================================

    @property
    def block3_taxonomies(self) -> Dict[str, Any]:
        """
        Taxonomies used by Block 3 (e.g. posture order).
        """
        return self.block3.get("taxonomies", {})

    @property
    def block3_thresholds(self) -> Dict[str, Any]:
        """
        Thresholds used by Block 3 analytical core.
        """
        return self.block3.get("thresholds", {})

    @property
    def block3_rules(self) -> Dict[str, Any]:
        """
        Structural rules for Block 3 processing.
        """
        return self.block3.get("rules", {})
        return self.block4_2.get("projection_policy", {})
# ==================================================
# BLOCK 2 — COUNTRY PROFILES
# ==================================================

    @property
    def block2_config(self) -> Dict[str, Any]:
        return self.block2
# ==================================================
# LOADER — ONLY PLACE WITH FILE I/O
# ==================================================

def load_block4_config(path: Path) -> Block4Config:
    """
    Load block4.yaml from disk and return a Block4Config instance.

    This is the ONLY place where file I/O is allowed.
    """

    if not path.exists():
        raise Block4ConfigError(f"Missing block4 config file: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return Block4Config(raw)
