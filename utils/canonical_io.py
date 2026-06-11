from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """
    Append-only JSONL writer (one object per line).
    Ensures parent directory exists and writes UTF-8.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(obj, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_jsonl(
    path: Path,
    limit: Optional[int] = None,
    reverse: bool = False,
) -> List[Dict[str, Any]]:
    """
    Load JSONL into memory.
    - limit: if set, returns only N entries
    - reverse: if True, returns newest-first (reads all then reverses)
    """
    path = Path(path)
    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    if reverse:
        rows.reverse()

    if limit is not None:
        return rows[:limit]

    return rows
