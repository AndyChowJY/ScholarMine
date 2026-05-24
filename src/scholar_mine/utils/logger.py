"""Structured logging with rotation and per-paper detail logs."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class Logger:
    """Centralized logger for ScholarMine pipeline and agent.

    Creates:
    - Main pipeline log: logs/pipeline_YYYYMMDD_HHMMSS.log
    - Per-paper logs: logs/per_paper/paper_NNN.log
    - Error log: logs/errors/errors.log
    """

    _instance: Optional["Logger"] = None

    def __init__(self, log_dir: str = "logs", level: str = "INFO",
                 per_paper: bool = True, rotate_days: int = 30):
        self.log_dir = Path(log_dir)
        self.per_paper_enabled = per_paper
        self._level = getattr(logging, level.upper(), logging.INFO)

        # Ensure directories exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        if per_paper:
            (self.log_dir / "per_paper").mkdir(exist_ok=True)
        (self.log_dir / "errors").mkdir(exist_ok=True)

        # Create main logger
        self.logger = logging.getLogger("ScholarMine")
        self.logger.setLevel(self._level)
        self.logger.handlers.clear()

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self._level)
        ch.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-7s %(message)s", datefmt="%H:%M:%S"
        ))
        self.logger.addHandler(ch)

        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fh = RotatingFileHandler(
            self.log_dir / f"pipeline_{timestamp}.log",
            maxBytes=10 * 1024 * 1024, backupCount=rotate_days
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-7s [%(name)s] %(message)s"
        ))
        self.logger.addHandler(fh)

        # Error file handler
        eh = RotatingFileHandler(
            self.log_dir / "errors" / "errors.log",
            maxBytes=5 * 1024 * 1024, backupCount=10
        )
        eh.setLevel(logging.ERROR)
        eh.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s %(message)s"
        ))
        self.logger.addHandler(eh)

        Logger._instance = self

    @classmethod
    def get(cls) -> "Logger":
        """Get the singleton logger instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_paper_logger(self, paper_id: str) -> logging.Logger:
        """Create a per-paper detail logger."""
        plog = logging.getLogger(f"ScholarMine.paper.{paper_id}")
        plog.setLevel(logging.DEBUG)
        plog.handlers.clear()
        fh = logging.FileHandler(
            self.log_dir / "per_paper" / f"{paper_id}.log", encoding="utf-8"
        )
        fh.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
        plog.addHandler(fh)
        plog.propagate = False
        return plog

    def info(self, msg: str):   self.logger.info(msg)
    def debug(self, msg: str):  self.logger.debug(msg)
    def warning(self, msg: str): self.logger.warning(msg)
    def error(self, msg: str):  self.logger.error(msg)
    def critical(self, msg: str): self.logger.critical(msg)