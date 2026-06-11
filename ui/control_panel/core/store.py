from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple, List
import hashlib
import json
import subprocess
import yaml


@dataclass
class Paths:
    project_root: Path
    config_dir: Path
    snapshot_dir: Path


def get_paths(app_file: str) -> Paths:
    project_root = Path(app_file).resolve().parents[2]  # ui/control_panel/app.py -> project root
    config_dir = project_root / "config"
    snapshot_dir = config_dir / "_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    return Paths(project_root=project_root, config_dir=config_dir, snapshot_dir=snapshot_dir)


def load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def md5_text(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def snapshot_yaml(paths: Paths, source_path: Path, data: Any) -> Tuple[Path, Path]:
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    h = md5_text(content)[:12]

    folder = paths.snapshot_dir / source_path.stem
    folder.mkdir(parents=True, exist_ok=True)

    snap_path = folder / f"{stamp}__{h}.yaml"
    meta_path = folder / f"{stamp}__{h}.meta.json"

    snap_path.write_text(content, encoding="utf-8")
    meta = {
        "source_file": str(source_path),
        "created_at_utc": stamp,
        "hash_md5": md5_text(content),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return snap_path, meta_path


def run_cmd(project_root: Path, cmd: List[str]) -> Tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
        )
        out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
        return p.returncode, out.strip()
    except Exception as e:
        return 1, str(e)
