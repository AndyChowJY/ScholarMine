"""Pipeline checkpoint system — enables resume from any stage."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class Checkpoint:
    """Stage-level checkpoint manager.

    Writes _sN_done marker files with stats.
    Pipeline resume reads these to skip completed stages.
    """

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _marker_path(self, stage: int) -> Path:
        return self.workspace / f"_s{stage}_done.json"

    def is_done(self, stage: int) -> bool:
        """Check if a stage has completed successfully."""
        path = self._marker_path(stage)
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("status") == "ok"
        except (json.JSONDecodeError, KeyError):
            return False

    def mark_done(self, stage: int, stats: Optional[Dict[str, Any]] = None):
        """Mark a stage as successfully completed."""
        data = {
            "status": "ok",
            "stage": stage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": stats or {},
        }
        self._marker_path(stage).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def mark_failed(self, stage: int, error: str):
        """Mark a stage as failed (for retry decisions)."""
        data = {
            "status": "failed",
            "stage": stage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }
        self._marker_path(stage).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def reset(self, stage: int):
        """Remove marker so stage can be re-run."""
        p = self._marker_path(stage)
        if p.exists():
            p.unlink()

    def reset_all(self):
        """Remove all stage markers."""
        for p in self.workspace.glob("_s*_done.json"):
            p.unlink()

    def status_summary(self) -> Dict[int, str]:
        """Return {stage: status} for all 5 stages."""
        return {
            i: "ok" if self.is_done(i) else "pending"
            for i in range(1, 6)
        }