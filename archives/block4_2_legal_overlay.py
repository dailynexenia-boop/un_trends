import sys
import json
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
from openai import OpenAI
import os

# ----------------------------
# PATHS
# ----------------------------

BASE_DIR = Path(__file__).resolve().parent
SUBJECTS_DIR = BASE_DIR / "subjects"
CANONICAL_DIR = BASE_DIR / "canonical"
ARGUMENT_DIR = BASE_DIR / "legal_overlay" / "argument_sets"

# ----------------------------
# OPENAI
# ----------------------------

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# CLI
# ----------------------------

SESSION_ID = sys.argv[1]
SUBJECT = sys.argv[2]
ARGUMENT_SET = sys.argv[3]  # ex: unilateral_measures, palestine

# ----------------------------
# LOAD ARGUMENT SET
# ----------------------------

arg_path = ARGUMENT_DIR / f"{ARGUMENT_SET}.json"
LEGAL_ARGUMENTS = json.load(open(arg_path, encoding="utf-8"))

# ----------------------------
# LOAD DATA
# ----------------------------

cards = json.load(open(SUBJECTS_DIR / f"{SESSION_ID}_block4_subject_cards_v1.json", encoding="utf-8"))
card = next(c for c in cards if c["subject"].lower() == SUBJECT.lower())
entry_ids = set(card["trace"]["entry_ids_all"])

entries = []
for line in open(CANONICAL_DIR / f"{SESSION_ID}_entries_with_speaker.jsonl", encoding="utf-8"):
    e = json.loads(line)
    if e.get("entry_id") in entry_ids:
        entries.append(e["signals_text"])

# ----------------------------
# GPT PROMPT
# ----------------------------

PROMPT = f"""
You analyze UN Human Rights Council statements.

For the text below, return ONLY a JSON list of argument keys
chosen STRICTLY from this list:

{json.dumps(list(LEGAL_ARGUMENTS.keys()), indent=2)}

If none apply, return [].

Text:
"""

counter = Counter()

for text in entries:
    r = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": PROMPT + text}],
        temperature=0
    )
    keys = json.loads(r.choices[0].message.content)
    counter.update(keys)

# ----------------------------
# CLASSIFICATION
# ----------------------------

high = [k for k, v in counter.items() if v >= 8]
emerging = [k for k, v in counter.items() if 2 <= v <= 4]
low = [k for k, v in counter.items() if v == 1]

# ----------------------------
# OUTPUT
# ----------------------------

output = {
    "session_id": SESSION_ID,
    "subject": SUBJECT,
    "argument_set": ARGUMENT_SET,
    "arguments": {
        "high_resonance": high,
        "emerging_angles": emerging,
        "logical_but_low_impact": low
    }
}

print(json.dumps(output, indent=2))
