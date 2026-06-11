# -*- coding: utf-8 -*-
"""
Block 4.2 — Argumentative Core

Responsibilities:
- Interpret raw argumentative projections
- Measure resonance across entries
- Classify arguments into stable analytical categories
- Produce a transparent trace

NO LLM.
NO canonical loading.
NO business logic outside interpretation.
"""

from collections import Counter, defaultdict
from typing import List, Dict, Any



# --------------------------------------------------
# CORE
# --------------------------------------------------

def analyze_argument_resonance(
    projections: List[Dict[str, Any]],
    cfg_block4_2: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Analyze resonance of argumentative projections.

    projections:
    [
      {
        "entry_id": str,
        "arguments": [str, ...]
      }
    ]
    """

    argument_sets = cfg_block4_2.get("argument_sets", {})
    thresholds = cfg_block4_2.get("resonance_thresholds", {})

    # --------------------------------------------------
    # 1. Count arguments + trace entries
    # --------------------------------------------------

    counts = Counter()
    trace = defaultdict(list)

    for p in projections:
        entry_id = p.get("entry_id")
        args = p.get("arguments", [])

        if not entry_id or not isinstance(args, list):
            continue

        for a in args:
            counts[a] += 1
            trace[a].append(entry_id)

    # --------------------------------------------------
    # 2. Interpret thresholds
    # --------------------------------------------------

    def _threshold(name: str) -> Dict[str, Any]:
        return thresholds.get(name, {})

    high_cfg = _threshold("high_resonance")
    emerging_cfg = _threshold("emerging")
    marginal_cfg = _threshold("marginal")

    high = []
    emerging = []
    low = []

    for arg, n in counts.items():
        if n >= high_cfg.get("min_hits", 999):
            high.append(arg)
        elif (
            emerging_cfg.get("min_hits", 0)
            <= n
            <= emerging_cfg.get("max_hits", -1)
        ):
            emerging.append(arg)
        elif n == marginal_cfg.get("exact_hits", 1):
            low.append(arg)

    # --------------------------------------------------
    # 3. Stable ordering (deterministic output)
    # --------------------------------------------------

    high.sort(key=lambda a: (-counts[a], a))
    emerging.sort(key=lambda a: (-counts[a], a))
    low.sort(key=lambda a: (-counts[a], a))

    # --------------------------------------------------
    # 4. Output
    # --------------------------------------------------

    return {
        "arguments": {
            "high_resonance": high,
            "emerging_angles": emerging,
            "logical_but_low_impact": low,
        },
        "trace": {
            "counts": dict(counts),
            "entries_per_argument": dict(trace),
            "total_entries": len({p.get("entry_id") for p in projections}),
        },
    }
