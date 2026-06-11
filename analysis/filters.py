# analysis/filters.py

from typing import Dict, Any, Callable, Iterable


def normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


# -----------------------------
# Structural predicates
# -----------------------------

def has_country(entry: Dict[str, Any]) -> bool:
    return bool(entry.get("country"))


def has_keywords(entry: Dict[str, Any]) -> bool:
    return bool(entry.get("keywords"))


def is_state_actor(entry: Dict[str, Any]) -> bool:
    return entry.get("primary_speaker_type") == "state"


# -----------------------------
# Generic filters
# -----------------------------

def filter_entries(
    entries: Iterable[Dict[str, Any]],
    predicate: Callable[[Dict[str, Any]], bool],
):
    return [e for e in entries if predicate(e)]


def filter_dict_by_threshold(
    data: Dict[str, int],
    max_value: int,
):
    return {
        k: v for k, v in data.items()
        if v <= max_value
    }
