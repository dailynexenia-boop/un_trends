import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from ui.control_panel.core.store import (
    load_yaml,
    snapshot_yaml,
    run_cmd,
)

# =========================================================
# HELPERS
# =========================================================

def file_mtime(path: Path):
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime)


def list_snapshots(snapshot_dir: Path, limit: int = 10):
    if not snapshot_dir.exists():
        return []
    snaps = sorted(
        snapshot_dir.glob("**/*.yaml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return snaps[:limit]


def format_dt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "—"


# =========================================================
# PAGE
# =========================================================

def render(
    config_dir: Path,
    ui_desc: Dict[str, Any],
    project_root: Path,
    snapshot_dir: Path,
):
    st.subheader("Recompute & History")
    st.caption(
        "System state, configuration history, and safe application of changes."
    )

    # =====================================================
    # SYSTEM STATUS
    # =====================================================

    st.markdown("### System status")

    block4 = config_dir / "block4.yaml"
    canonical = project_root / "canonical" / "canonical.jsonl"

    last_config_change = file_mtime(block4)
    last_recompute = file_mtime(canonical)
    snapshots = list_snapshots(snapshot_dir, limit=1)

    col1, col2 = st.columns(2)

    with col1:
        if last_config_change and last_recompute:
            if last_config_change > last_recompute:
                st.warning("Configuration changed since last recompute")
            else:
                st.success("Configuration is applied")
        elif last_config_change:
            st.warning("Configuration changed (no recompute yet)")
        else:
            st.info("No configuration changes detected")

        st.markdown(f"**Last config change:** {format_dt(last_config_change)}")

    with col2:
        st.markdown(f"**Last recompute:** {format_dt(last_recompute)}")
        if snapshots:
            st.markdown(f"**Last snapshot:** {snapshots[0].name}")
        else:
            st.markdown("**Last snapshot:** None")

    # Gentle UX hint
    if last_config_change and not snapshots:
        st.info(
            "Changes have been made, but no snapshot exists yet. "
            "Consider creating a snapshot before applying changes."
        )

    # =====================================================
    # ACTIONS (SAFE ONLY)
    # =====================================================

    st.markdown("### Actions")
    st.caption(
        "These actions are safe and recommended. "
        "They preserve history and apply changes consistently."
    )

    col3, col4, col5 = st.columns(3)

    # -----------------------------------------------------
    # SAVE (noop but explicit)
    # -----------------------------------------------------
    with col3:
        if st.button("💾 Save configuration"):
            st.success(
                "Configuration files are already saved on disk."
            )

    # -----------------------------------------------------
    # SNAPSHOT
    # -----------------------------------------------------
    with col4:
        if st.button("🧾 Create full snapshot"):
            snapshot_count = 0
            for p in config_dir.glob("*.yaml"):
                data = load_yaml(p)
                snapshot_yaml(
                    type("SnapshotCtx", (), {"snapshot_dir": snapshot_dir})(),
                    p,
                    data,
                )
                snapshot_count += 1

            st.success(
                f"Snapshot created for {snapshot_count} configuration files."
            )

    # -----------------------------------------------------
    # RECOMPUTE (SINGLE SAFE PIPELINE)
    # -----------------------------------------------------
    with col5:
        if st.button("🔁 Apply changes (recompute)"):
            code, out = run_cmd(
                project_root,
                ["python", "analysis/recompute_canonical.py", "--all"],
            )

            st.text_area(
                "Recompute logs",
                value=out or "Completed.",
                height=260,
            )

    # -----------------------------------------------------
    # PULL FROM GITHUB (sync local from cloud entries)
    # -----------------------------------------------------
    st.divider()
    st.markdown("### Pull from GitHub")
    st.caption("Récupère les entrées saisies depuis la tablette en session. À faire avant de travailler en local après une session.")

    if st.button("⬇️ Pull from GitHub"):
        code, out = run_cmd(project_root, ["git", "pull"])
        if code == 0:
            st.success("Local is up to date with GitHub.")
            if out.strip():
                st.caption(out.strip()[:300])
        else:
            st.error(f"Pull failed: {out.strip()[:300]}")

    # -----------------------------------------------------
    # SYNC TO GITHUB (push canonical + config)
    # -----------------------------------------------------
    st.divider()
    st.markdown("### Sync to cloud")
    st.caption("Pushes canonical data and config to GitHub so the deployed app sees the latest data.")

    token = None
    try:
        token = st.secrets.get("GITHUB_TOKEN")
    except Exception:
        pass

    if not token:
        st.warning("GITHUB_TOKEN not found in secrets — sync unavailable.")
    else:
        if st.button("☁️ Push to GitHub"):
            import subprocess
            from datetime import datetime

            stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            remote = f"https://x-access-token:{token}@github.com/dailynexenia-boop/un_trends.git"

            cmds = [
                ["git", "add", "canonical/canonical.jsonl", "config/"],
                ["git", "commit", "--allow-empty", "-m", f"Sync canonical — {stamp}"],
                ["git", "push", remote, "main"],
            ]

            logs = []
            ok = True
            for cmd in cmds:
                p = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True)
                logs.append((cmd[1], p.returncode, (p.stdout or "") + (p.stderr or "")))
                if p.returncode != 0 and cmd[1] != "commit":
                    ok = False
                    break

            for name, code, out in logs:
                if out.strip():
                    st.caption(f"`{name}` → {'✅' if code == 0 else '❌'} {out.strip()[:200]}")

            if ok:
                st.success("Pushed. Streamlit Cloud will update in ~1 minute.")

    # =====================================================
    # HISTORY
    # =====================================================

    st.markdown("### Recent history")

    snapshots = list_snapshots(snapshot_dir, limit=10)

    if snapshots:
        for s in snapshots:
            st.markdown(
                f"- **{s.name}** — {format_dt(file_mtime(s))}"
            )
    else:
        st.info(
            "No snapshots yet.\n\n"
            "Snapshots are created only when you explicitly choose to do so. "
            "Once created, previous configuration versions will appear here."
        )
