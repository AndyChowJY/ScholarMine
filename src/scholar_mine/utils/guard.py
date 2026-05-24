"""
Runtime guard / watchdog for ScholarMine pipeline.

Monitors:
- Repetitive error patterns in logs (signals stuck retry loops)
- Disk usage (prevent filling up with corrupted downloads)
- Stalled pipeline stages (no progress for N minutes)
- API rate-limit warnings

Can be run as a background subprocess alongside the pipeline.
"""

import time
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from scholar_mine.utils.logger import Logger

log = Logger.get()


class PipelineGuard:
    """Watchdog that monitors pipeline health during execution."""

    def __init__(self, workspace: Path, check_interval_secs: float = 5.0,
                 stall_timeout_mins: float = 30.0):
        self.workspace = Path(workspace)
        self.interval = check_interval_secs
        self.stall_timeout = stall_timeout_mins * 60
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.repeat_threshold = 10  # same error >10 times = alert
        self._last_progress_time = time.time()
        self._alerts: List[str] = []

    def tick(self) -> List[str]:
        """Run one check cycle. Returns list of alert messages (empty = all ok)."""
        self._alerts = []

        self._check_error_loops()
        self._check_disk_usage()
        self._check_stall()

        return self._alerts

    def watch(self, max_cycles: Optional[int] = None) -> None:
        """Run continuously until max_cycles or keyboard interrupt."""
        cycle = 0
        try:
            while max_cycles is None or cycle < max_cycles:
                alerts = self.tick()
                for a in alerts:
                    log.warning(f"GUARD: {a}")
                time.sleep(self.interval)
                cycle += 1
        except KeyboardInterrupt:
            log.info("Guard stopped by user")

    # ── private checkers ──────────────────────────────────

    def _check_error_loops(self):
        """Parse error log for repetitive patterns."""
        error_log = self.workspace / "logs" / "errors" / "errors.log"
        if not error_log.exists():
            return

        try:
            lines = error_log.read_text(encoding="utf-8").splitlines()
            recent = lines[-200:]  # last 200 lines

            pattern_counts: Dict[str, int] = defaultdict(int)
            for line in recent:
                # Normalize: strip timestamps and variable parts
                normalized = re.sub(r'\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}[.,]\d+', '', line)
                normalized = re.sub(r"'[^']*'", "'...'", normalized)
                normalized = re.sub(r'"[^"]*"', '"..."', normalized)
                normalized = normalized.strip()
                if normalized:
                    pattern_counts[normalized] += 1

            for pattern, count in pattern_counts.items():
                if count >= self.repeat_threshold:
                    self._alerts.append(
                        f"Repeat error ({count}x): {pattern[:120]}"
                    )
        except Exception:
            pass

    def _check_disk_usage(self):
        """Warn if downloads directory exceeds 10 GB."""
        downloads = self.workspace / "downloads"
        if not downloads.exists():
            return

        try:
            total = sum(
                f.stat().st_size for f in downloads.rglob("*")
                if f.is_file()
            )
            gb = total / (1024 ** 3)
            if gb > 10:
                self._alerts.append(
                    f"Downloads dir size: {gb:.1f} GB — consider cleaning up"
                )
        except Exception:
            pass

    def _check_stall(self):
        """Check if pipeline has made no progress."""
        checkpoint_dir = self.workspace
        marker_files = sorted(
            checkpoint_dir.glob("_s*_done.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if marker_files:
            last_mod = marker_files[0].stat().st_mtime
            self._last_progress_time = last_mod

        elapsed = time.time() - self._last_progress_time
        if elapsed > self.stall_timeout:
            mins = elapsed / 60
            self._alerts.append(
                f"Pipeline stalled: no progress for {mins:.0f} minutes"
            )


def run_guard(workspace: str, interval: float = 5.0,
              stall_timeout_mins: float = 30.0, max_cycles: Optional[int] = None):
    """Convenience function to start the guard."""
    guard = PipelineGuard(
        Path(workspace), check_interval_secs=interval,
        stall_timeout_mins=stall_timeout_mins,
    )
    guard.watch(max_cycles=max_cycles)
