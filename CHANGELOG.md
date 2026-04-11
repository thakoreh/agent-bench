# Changelog

## 0.4.1 (2026-04-11)

### Bug Fixes
- Fixed 3 failing tests: `--compare` takes 2 separate args (not comma-separated), `Config.get_agent_config()` returns `{}` not `None`, empty model string handled gracefully

### Tests
- 49 new edge case tests (229 total)
- Full coverage: collector, scorer, pricing, config, storage, reporter
- Letter grade boundary testing
- Import issue detection edge cases

## 0.4.0 (2026-04-09)

### New Features
- **CSV export**: `agent-bench results --csv -o results.csv` exports all metrics
- **Leaderboard command**: `agent-bench leaderboard` aggregates scores across all runs (avg, best, wins, total runs)
- **Scoring breakdown**: `agent-bench results --breakdown` shows per-factor scoring (test pass rate, lint, diff, speed, etc.)
- **History JSON**: `agent-bench history --json` for programmatic access
- **Cost efficiency metric**: `quality_score / max(cost, 0.01)` column in results table
- **Sort by cost efficiency**: `agent-bench results --sort-by cost-efficiency`

### Tests
- 19 new tests (166 total)
- Edge case coverage: empty leaderboard, special characters in CSV, zero-metric breakdown, empty history JSON

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
