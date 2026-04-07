"""Config file handling for agent-bench."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml


DEFAULT_CONFIG_NAME = ".agent-bench.yaml"
DEFAULT_CONFIG_PATHS = [Path(DEFAULT_CONFIG_NAME), Path.home() / ".agent-bench.yaml"]

DEFAULT_CONFIG: dict[str, Any] = {
    "agents": {
        "claude-code": {"command": "claude", "args": ["--dangerously-skip-permissions"]},
        "codex-cli": {"command": "codex", "args": ["--full-auto"]},
        "openclaw": {"command": "openclaw", "args": []},
        "aider": {"command": "aider", "args": ["--yes-always"]},
    },
    "default-task": "Refactor this file to use type hints throughout",
    "scoring": {
        "run-tests": True,
        "lint": True,
        "timeout": 300,
    },
}


class Config:
    """Manages agent-bench configuration."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or self._find_config()
        self._data: dict[str, Any] = {}
        if self.path and self.path.exists():
            self._load()
        else:
            self._data = dict(DEFAULT_CONFIG)

    def _find_config(self) -> Optional[Path]:
        for p in DEFAULT_CONFIG_PATHS:
            if p.exists():
                return p
        return None

    def _load(self) -> None:
        with open(self.path) as f:
            self._data = yaml.safe_load(f) or {}
        # Merge defaults for missing sections
        for key, val in DEFAULT_CONFIG.items():
            if key not in self._data:
                self._data[key] = val

    def save(self, path: Optional[Path] = None) -> Path:
        target = path or self.path or Path(DEFAULT_CONFIG_NAME)
        with open(target, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False, sort_keys=False)
        self.path = target
        return target

    @property
    def agents(self) -> dict[str, dict[str, Any]]:
        return self._data.get("agents", {})

    @property
    def default_task(self) -> str:
        return self._data.get("default-task", "")

    @property
    def scoring(self) -> dict[str, Any]:
        return self._data.get("scoring", {})

    @property
    def timeout(self) -> int:
        return self.scoring.get("timeout", 300)

    @property
    def run_tests(self) -> bool:
        return self.scoring.get("run-tests", True)

    @property
    def run_lint(self) -> bool:
        return self.scoring.get("lint", True)

    def get_agent_config(self, name: str) -> dict[str, Any]:
        return self.agents.get(name, {})

    @property
    def data(self) -> dict[str, Any]:
        return dict(self._data)
