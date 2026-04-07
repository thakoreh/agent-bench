"""Detect installed AI coding agents."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class AgentInfo:
    """Information about a detected agent."""
    name: str
    installed: bool = False
    path: str = ""
    version: str = ""

    def __str__(self) -> str:
        if not self.installed:
            return f"{self.name}: not found"
        v = f" ({self.version})" if self.version else ""
        return f"{self.name}: {self.path}{v}"


# Known agents and their version flags
KNOWN_AGENTS: dict[str, list[str]] = {
    "claude-code": ["claude", "--version"],
    "codex-cli": ["codex", "--version"],
    "gemini-cli": ["gemini", "--version"],
    "openclaw": ["openclaw", "--version"],
    "aider": ["aider", "--version"],
    "hermes": ["hermes", "--version"],
    "opencode": ["opencode", "--version"],
}

# Map binary names to agent names for detection
BINARY_MAP: dict[str, str] = {
    "claude": "claude-code",
    "codex": "codex-cli",
    "gemini": "gemini-cli",
    "openclaw": "openclaw",
    "aider": "aider",
    "hermes": "hermes",
    "opencode": "opencode",
}


def detect_agent(name: str) -> AgentInfo:
    """Detect if a specific agent is installed."""
    info = AgentInfo(name=name)

    # Get the command/binary name
    cmd = name
    version_args = ["--version"]
    for agent_name, args in KNOWN_AGENTS.items():
        if agent_name == name:
            cmd = args[0]
            version_args = args[1:]
            break

    # Check if binary exists
    path = shutil.which(cmd)
    if not path:
        return info

    info.installed = True
    info.path = path

    # Try to get version
    try:
        result = subprocess.run(
            [cmd] + version_args,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = (result.stdout or result.stderr).strip()
        # Take first line, limit length
        if output:
            info.version = output.split("\n")[0][:80]
    except (subprocess.TimeoutExpired, OSError):
        pass

    return info


def detect_all() -> list[AgentInfo]:
    """Detect all known agents."""
    return [detect_agent(name) for name in KNOWN_AGENTS]


def detect_from_config(agents: dict[str, dict]) -> list[AgentInfo]:
    """Detect agents from config dictionary."""
    results = []
    for name, cfg in agents.items():
        binary = cfg.get("command", name)
        # Use binary lookup
        agent_name = BINARY_MAP.get(binary, name)
        info = detect_agent(agent_name)
        info.name = name  # Use config name
        results.append(info)
    return results
