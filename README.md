# agent-bench

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://github.com/thakoreh/agent-bench)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 96](https://img.shields.io/badge/tests-96%20passed-brightgreen.svg)]


Benchmark AI coding agents against each other on the same task.

Run the **same coding task** across Claude Code, Codex CLI, Gemini CLI, Aider, OpenClaw, and more — then compare cost, speed, token usage, code quality, and test pass rate.

## Why?

No existing tool lets regular devs compare AI coding agents head-to-head on **their** codebase. Terminal-Bench is academic. This is practical.

## Install

```bash
pip install cli-agent-bench
```

## Quick Start

```bash
# Create config
agent-bench init

# Edit .agent-bench.yaml with your task and agents

# Run all configured agents
agent-bench run

# Run specific agents
agent-bench run --agent claude-code,codex-cli

# Override the task
agent-bench run --task "Add error handling to all API calls"

# View results
agent-bench results

# JSON output
agent-bench results --json

# View history
agent-bench history

# Check which agents are installed
agent-bench agents
```

## Example Output

```
╭─────────────────── Agent Benchmark Results ────────────────────╮
│ Task: "Add pagination to users endpoint"                        │
│ Run: 2026-04-07 00:15                                          │
├──────────┬──────────┬───────┬──────────┬────────┬──────────────┤
│ Agent    │ Time     │ Cost  │ Tokens   │ Tests  │ Quality      │
├──────────┼──────────┼──────────┼────────┼────────┼──────────────┤
│ Claude   │ 2m 14s   │ $0.42 │ 18.2K    │ 8/8 ✅ │ A (92/100)   │
│ Codex    │ 1m 47s   │ $0.31 │ 14.1K    │ 8/8 ✅ │ A- (88/100)  │
│ Gemini   │ 3m 02s   │ $0.18 │ 22.3K    │ 7/8 ⚠️ │ B+ (81/100)  │
│ Aider    │ 4m 15s   │ $0.55 │ 31.0K    │ 6/8 ❌ │ B (75/100)   │
╰──────────┴──────────┴───────┴──────────┴────────┴──────────────╯

Winner: Claude Code (A — best quality)
Fastest: Codex CLI (1m 47s)
Cheapest: Gemini CLI ($0.18)
```

## Configuration

`.agent-bench.yaml`:

```yaml
agents:
  claude-code:
    command: claude
    args: ["--dangerously-skip-permissions"]
  codex-cli:
    command: codex
    args: ["--full-auto"]
  aider:
    command: aider
    args: ["--yes-always"]

default-task: "Refactor this file to use type hints throughout"

scoring:
  run-tests: true
  lint: true
  timeout: 300
```

## Quality Score

| Component | Weight |
|-----------|--------|
| Test pass rate | 40% |
| Lint clean | 20% |
| Code diff sensibility | 15% |
| Task completion | 15% |
| Speed bonus | 10% |

## How It Works

1. Copies your project to an isolated temp directory per agent
2. Runs each agent as a subprocess with the task prompt
3. Captures stdout/stderr, exit code, duration
4. Parses token usage from output
5. Runs tests and linter if configured
6. Calculates cost from token usage + model pricing
7. Scores quality across multiple dimensions
8. Stores results in SQLite for history
9. Cleans up temp directories

## Supported Agents

Any CLI-based coding agent: Claude Code, Codex CLI, Gemini CLI, Aider, OpenClaw, Hermes, OpenCode, and more. If it runs in a terminal, it works.

## License

MIT © Hiren Thakore
