import json
import yaml
import re
from pathlib import Path

# -----------------------------
# PATHS
# -----------------------------
from pathlib import Path
import yaml

# =========================
# PATHS (ROOT-BASED)
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"

# =========================
# LOAD YAML REGISTERS
# =========================

def load_registers():
    path = CONFIG_DIR / "topic_position_registers.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

REGISTERS = load_registers()
SENSITIVE_TOPICS = {
    "PALESTINE",
    "UKRAINE",
    "HONG_KONG_CHINA"
}

# -----------------------------
# TEXT NORMALIZATION
# -----------------------------
def normalize(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text

def get_texts(entry):
    signals_text = normalize(entry.get("signals_text", "") or "")
    keywords_text = normalize(" ".join(entry.get("keywords", [])))
    full_text = normalize(f"{signals_text} {keywords_text}")
    return signals_text, full_text

# -----------------------------
# SIGNAL STRUCTURE
# -----------------------------
def infer_signal_structure(text):
    if ";" in text and "," in text:
        form = "mixed"
    elif ";" in text:
        form = "enumeration"
    else:
        form = "single_statement"

    focus = "multiple" if ";" in text else "single"

    return {"form": form, "focus": focus}

# -----------------------------
# TOPIC INFERENCE (V1.2)
# -----------------------------
def infer_topics(signals_text, full_text):
    detected = []

    for topic, positions in REGISTERS.items():
        match_full = False
        match_signal = False

        for terms in positions.values():
            for t in terms:
                t = t.lower()
                if t in full_text:
                    match_full = True
                if t in signals_text:
                    match_signal = True

        if not match_full:
            continue

        # sensitive topics must match signals_text
        if topic in SENSITIVE_TOPICS and not match_signal:
            continue

        detected.append(topic)

    central = detected[:1]
    secondary = detected[1:]

    return central, secondary

# -----------------------------
# TOPIC POSITIONS
# -----------------------------
def infer_topic_positions(text, topics):
    topic_positions = {}

    for topic in topics:
        registry = REGISTERS.get(topic, {})
        detected = {}

        for position, terms in registry.items():
            if any(t.lower() in text for t in terms):
                detected[position] = True

        if detected:
            topic_positions[topic] = detected

    return topic_positions

# -----------------------------
# DISCURSIVE GESTURE
# -----------------------------
def infer_discursive_gesture(text):
    if "announce" in text:
        return "announcement"
    if any(w in text for w in ["call", "urge", "request", "seek"]):
        return "appeal"
    if any(w in text for w in ["condemn", "oppose", "reject"]):
        return "positioning"
    if any(w in text for w in ["reaffirm", "reiterate", "stress"]):
        return "reaffirmation"
    return "statement"

# -----------------------------
# DIPLOMATIC POSTURE (V1.2)
# -----------------------------
def infer_diplomatic_posture(text):
    if any(w in text for w in [
        "genocide",
        "crimes against humanity",
        "illegal occupation",
        "intimidation"
    ]):
        return "assertive"

    if any(w in text for w in [
        "condemn",
        "aggression",
        "violation"
    ]):
        return "assertive"

    if any(w in text for w in [
        "protect",
        "ensure",
        "defend"
    ]):
        return "defensive"

    if any(w in text for w in [
        "cooperation",
        "support",
        "appreciation",
        "inclusive",
        "constructive",
        "universality",
        "equal treatment",
        "dialogue"
    ]):
        return "cooperative"

    return "passive"

# -----------------------------
# EXPLICITNESS & RISK
# -----------------------------
def infer_explicitness(text):
    if any(w in text for w in [
        "genocide",
        "war crimes",
        "crimes against humanity"
    ]):
        return "high"
    if "concern" in text or "undermine" in text:
        return "medium"
    return "low"

def infer_risk(text):
    if any(w in text for w in [
        "genocide",
        "illegal",
        "condemn"
    ]):
        return "high"
    if any(w in text for w in [
        "urge",
        "criticize"
    ]):
        return "medium"
    return "low"

# -----------------------------
# DIPLOMATIC ACTS
# -----------------------------
def infer_diplomatic_acts(text):
    return {
        "announcement": "announce" in text,
        "candidacy": any(w in text for w in ["candidacy", "candidate", "election"]),
        "initiative_launch": "launch an initiative" in text or "establish an initiative" in text,
        "invitation": "invite states" in text,
        "report_reference": any(w in text for w in ["report of", "special rapporteur", "commission of inquiry"]),
        "procedural_opening": any(w in text for w in ["agenda item", "bureau", "mandate"])
    }

# -----------------------------
# MAIN PROCESS
# -----------------------------
def process(infile, outfile):
    with open(infile, encoding="utf-8") as fin, \
         open(outfile, "w", encoding="utf-8") as fout:

        for line in fin:
            entry = json.loads(line)

            signals_text, full_text = get_texts(entry)

            central, secondary = infer_topics(signals_text, full_text)

            micro = {
                "signal_carriers": {
                    "text": bool(signals_text),
                    "keywords": bool(entry.get("keywords"))
                },
                "signal_structure": infer_signal_structure(signals_text),
                "topics_analysis": {
                    "central_topics": central,
                    "secondary_topics": secondary
                },
                "discursive_gesture": infer_discursive_gesture(full_text),
                "diplomatic_posture": infer_diplomatic_posture(full_text),
                "narrative_positioning": {
                    "frame": {
                        "primary": central[0] if central else "",
                        "secondary": secondary
                    },
                    "topic_positions": infer_topic_positions(full_text, central + secondary)
                },
                "explicitness_level": infer_explicitness(full_text),
                "risk_level": infer_risk(full_text),
                "diplomatic_acts": infer_diplomatic_acts(full_text)
            }

            micro["novelty_signal"] = (
                micro["explicitness_level"] == "high"
                or micro["risk_level"] == "high"
            )

            micro["watch_flag"] = (
                micro["novelty_signal"]
                or any(micro["diplomatic_acts"].values())
            )

            entry["micro_analysis"] = micro
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("[OK] Block1 micro-analysis V1.2 generated")
def build_micro_analysis(entry: dict) -> dict:
    """
    Build micro-analysis from a canonical entry dict.
    Shared by:
    - build_canonical.py (CSV batch)
    - editor.py (manual ingestion)
    """

    signals_text, full_text = get_texts(entry)
    central, secondary = infer_topics(signals_text, full_text)

    micro = {
        "signal_carriers": {
            "text": bool(signals_text),
            "keywords": bool(entry.get("keywords"))
        },
        "signal_structure": infer_signal_structure(signals_text),
        "topics_analysis": {
            "central_topics": central,
            "secondary_topics": secondary
        },
        "discursive_gesture": infer_discursive_gesture(full_text),
        "diplomatic_posture": infer_diplomatic_posture(full_text),
        "narrative_positioning": {
            "frame": {
                "primary": central[0] if central else "",
                "secondary": secondary
            },
            "topic_positions": infer_topic_positions(
                full_text,
                central + secondary
            )
        },
        "explicitness_level": infer_explicitness(full_text),
        "risk_level": infer_risk(full_text),
        "diplomatic_acts": infer_diplomatic_acts(full_text)
    }

    micro["novelty_signal"] = (
        micro["explicitness_level"] == "high"
        or micro["risk_level"] == "high"
    )

    micro["watch_flag"] = (
        micro["novelty_signal"]
        or any(micro["diplomatic_acts"].values())
    )

    return micro

# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    import sys
    process(Path(sys.argv[1]), Path(sys.argv[2]))
