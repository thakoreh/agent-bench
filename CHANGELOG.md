# Changelog

## 0.3.0 (2026-04-08)

### New Features
- **`--parallel` flag on `run`**: run agents simultaneously with `agent-bench run --parallel`
- **`--model` flag on `run`**: override model per agent with `agent-bench run --model gpt-4o,claude-sonnet-4`
- **`trend` command**: show quality score trends across runs with `--json` and `--agent` filters
- **`delete` command**: clean up old runs with `agent-bench delete <run-id> --force`
- **`Storage.delete_run`**: removes a run and all its results
- **`Storage.get_agent_history`**: query all results for a specific agent
- **Model field in storage**: agent_results now stores the model name

### Improvements
- 18 new tests (147 total)
- Better CLI discoverability (help text for new flags)

## 0.2.0 (2026-04-07)

### New Features
- **Web Reporter**: Self-contained HTML reports with inline SVG bar charts for quality scores, cost, and duration comparison (`agent-bench report --html -o report.html`)
- **HTML flag on results**: `agent-bench results --html` for quick HTML output
- **GitHub Actions integration**: `.github/workflows/benchmark.yml` for CI benchmarking on PRs
- **py.typed marker**: PEP 561 compliance for type hint consumers

### Improvements
- Comprehensive edge-case test coverage:
  - Scorer: zero duration, all pass/fail, high complexity, negative exit codes
  - Collector: empty output, partial token matches, mixed formats
  - Reporter: empty results, single agent, many agents, markdown escaping, baseline comparison
  - Storage: corrupt DB recovery, concurrent writes, large result sets
  - CLI: report command, HTML output, version check
- Version bumped from 0.1.0 to 0.2.0

## 0.1.0 (2026-04-05)

### Initial Release
- Multi-agent detection and execution
- Quality scoring (complexity, import hygiene, test pass rate, lint, speed)
- SQLite storage for run history
- Markdown and Rich table output
- `--compare` and `--baseline` flags for side-by-side comparison
- Parallel agent execution with ThreadPoolExecutor
- Model-level comparison support
