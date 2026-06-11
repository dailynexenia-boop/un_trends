import json
import yaml
from pathlib import Path
from typing import Dict, Any, List


# ==================================================
# PATHS
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"

MICRO_CONFIG_PATH = CONFIG_DIR / "micro_analysis.yaml"
TOPIC_REGISTERS_PATH = CONFIG_DIR / "topic_position_registers.yaml"


# ==================================================
# LOAD CONFIG
# ==================================================

def load_micro_config() -> Dict[str, Any]:
    with open(MICRO_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["micro_analysis"]


def load_topic_registers() -> Dict[str, Any]:
    with open(TOPIC_REGISTERS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ==================================================
# TEXT NORMALIZATION
# ==================================================

def normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def get_texts(entry: Dict[str, Any]):
    signals_text = normalize(entry.get("signals_text", ""))
    keywords_text = normalize(" ".join(entry.get("keywords", [])))
    full_text = f"{signals_text} {keywords_text}".strip()
    return signals_text, full_text


# ==================================================
# TOPICS — DETECTION (PURE)
# ==================================================

def infer_topics_raw(
    full_text: str,
    topic_registers: Dict[str, Any],
) -> List[str]:
    detected = []

    for topic, positions in topic_registers.items():
        for terms in positions.values():
            if any(t.lower() in full_text for t in terms):
                detected.append(topic)
                break

    return detected


def apply_topic_governance(
    detected: List[str],
    signals_text: str,
    cfg: Dict[str, Any],
    topic_registers: Dict[str, Any],
):
    """
    Governs topics exactly like V1.2:
    - sensitive topics must match SIGNAL text via registry terms
    - priority = order of detection
    """
    sensitive = set(cfg["sensitivity"]["enforced_signal_match"])
    filtered: List[str] = []

    for topic in detected:
        if topic in sensitive:
            registry = topic_registers.get(topic, {})
            signal_terms = [
                t.lower()
                for terms in registry.values()
                for t in terms
            ]
            if any(t in signals_text for t in signal_terms):
                filtered.append(topic)
        else:
            filtered.append(topic)

    max_central = cfg["central"]["max_items"]
    max_secondary = cfg["secondary"]["max_items"]

    central = filtered[:max_central]
    secondary = filtered[max_central : max_central + max_secondary]

    return central, secondary


# ==================================================
# SIGNAL STRUCTURE
# ==================================================

def infer_signal_structure(text: str, cfg: Dict[str, Any]) -> Dict[str, str]:
    for form, rule in cfg["forms"].items():
        if all(r in text for r in rule.get("requires", [])):
            detected_form = form
            break
    else:
        detected_form = cfg.get("default_form", "single_statement")

    focus_cfg = cfg["focus"]
    focus = (
        "multiple"
        if focus_cfg["multiple"]["trigger"] in text
        else focus_cfg.get("default", "single")
    )

    return {
        "form": detected_form,
        "focus": focus,
    }


# ==================================================
# GENERIC LEVEL INFERENCE
# (gesture / posture / explicitness / risk)
# ==================================================

def infer_level(text: str, cfg: Dict[str, Any]) -> str:
    for level in cfg.get("priority", []):
        keywords = cfg["mapping"].get(level, {}).get("keywords", [])
        if any(k in text for k in keywords):
            return level
    return cfg.get("default")


# ==================================================
# DIPLOMATIC ACTS
# ==================================================

def infer_diplomatic_acts(text: str, cfg: Dict[str, Any]) -> Dict[str, bool]:
    if not cfg.get("enabled", True):
        return {}

    acts = {}
    for act, rule in cfg["acts"].items():
        acts[act] = any(k in text for k in rule.get("keywords", []))
    return acts


# ==================================================
# WATCH FLAG (FULLY YAML-GOVERNED)
# ==================================================

def apply_watch_flag(micro: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
    if not cfg.get("enabled", True):
        return False

    triggers = cfg.get("triggers", {})

    if micro["explicitness_level"] in triggers.get("explicitness", []):
        return True

    if micro["risk_level"] in triggers.get("risk", []):
        return True

    if micro["diplomatic_posture"] in triggers.get("posture", []):
        return True

    acts_cfg = triggers.get("diplomatic_acts", {})
    if acts_cfg.get("any") and any(micro["diplomatic_acts"].values()):
        return True

    topics_cfg = triggers.get("topics", {})
    if topics_cfg.get("include"):
        if any(
            t in topics_cfg["include"]
            for t in micro["topics_analysis"]["central_topics"]
        ):
            return True

    return False


# ==================================================
# MAIN MICRO ANALYSIS BUILDER
# ==================================================

def build_micro_analysis(
    entry: Dict[str, Any],
    cfg: Dict[str, Any] | None = None,
    topic_registers: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if cfg is None:
        from analysis.micro_config_loader import load_micro_analysis_config
        cfg = load_micro_analysis_config(strict=False)
    if topic_registers is None:
        topic_registers = load_topic_registers()

    signals_text, full_text = get_texts(entry)

    detected_topics = infer_topics_raw(
        full_text,
        topic_registers,
    )

    central, secondary = apply_topic_governance(
        detected_topics,
        signals_text,
        cfg["topics"],
        topic_registers,
    )

    micro = {
        "signal_carriers": {
            "text": bool(signals_text),
            "keywords": bool(entry.get("keywords")),
        },
        "signal_structure": infer_signal_structure(
            signals_text,
            cfg["signal_structure"],
        ),
        "topics_analysis": {
            "central_topics": central,
            "secondary_topics": secondary,
        },
        "discursive_gesture": infer_level(
            full_text,
            cfg["discursive_gestures"],
        ),
        "diplomatic_posture": infer_level(
            full_text,
            cfg["diplomatic_posture"],
        ),
        "explicitness_level": infer_level(
            full_text,
            cfg["explicitness"],
        ),
        "risk_level": infer_level(
            full_text,
            cfg["risk"],
        ),
        "diplomatic_acts": infer_diplomatic_acts(
            full_text,
            cfg["diplomatic_acts"],
        ),
    }

    micro["watch_flag"] = apply_watch_flag(
        micro,
        cfg["watch_flag"],
    )

    return micro


# ==================================================
# CLI (OPTIONAL BATCH MODE)
# ==================================================

def process(infile: Path, outfile: Path):
    with open(infile, encoding="utf-8") as fin, \
         open(outfile, "w", encoding="utf-8") as fout:

        for line in fin:
            entry = json.loads(line)
            entry["micro_analysis"] = build_micro_analysis(entry)
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("[OK] micro_analysis generated (YAML-governed, audited)")


if __name__ == "__main__":
    import sys
    process(Path(sys.argv[1]), Path(sys.argv[2]))
