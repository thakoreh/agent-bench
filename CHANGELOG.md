# Changelog

## 0.7.1 (2026-05-27)

### New Features
- **Expanded agent detection**: Added cursor, kiro, auggie, goose to KNOWN_AGENTS and BINARY_MAP (11 agents total)
- **Additional token parsing patterns**: 5 new regex patterns for Codex CLI, Gemini multiline, OpenAI API, Anthropic API, and compact formats (8 patterns total)
- **Storage utility methods**: `get_all_agent_names()`, `get_run_count()`, `get_agent_stats()` for aggregate analysis
- **Agent statistics**: Per-agent aggregate stats (avg/best/worst score, total tokens, total cost, test pass rate)

### Tests
- 27 new tests for v0.7.1 features
- Expanded detector: 10 tests (agent registration, binary map, detection)
- Expanded token patterns: 11 tests (Codex, Gemini, OpenAI, Anthropic, compact formats, edge cases)
- New storage methods: 8 tests (agent names, run count, aggregate stats, isolation)
- All 360 tests passing


## 0.6.0 (2026-05-25)

### New Features
- **Comment density scoring**: `compute_comment_density()` — measures comment-to-code ratio, sweet spot 10-30% (5% weight)
- **Code cleanliness scoring**: `_code_cleanliness_penalty()` — detects crashes, tracebacks, segfaults in output (4% weight)
- **Radar/spider charts in HTML reports**: SVG-based radar charts showing scoring breakdown across all 11 factors for each agent
- **Updated scoring formula**: Rebalanced from 9 factors to 11 factors (100 points total)

### Improvements
- **Scoring breakdown now shows 11 factors** (was 9): includes comment_density and code_cleanliness
- **Web reporter** now includes interactive radar charts with per-agent visual breakdown
- **Reporter breakdown** recalculated to match new scorer weights (25/12/10/10/7/7/6/7/7/5/4)
- **Version sync**: pyproject.toml, __init__.py, and footer all now show 0.6.0

### Tests
- 18 new tests for v0.6.0 features
- Comment density: empty, whitespace, no comments, all comments, mixed, docstrings
- Code cleanliness: clean output, traceback, syntax error, severe crashes
- Updated scoring weight validation
- Radar chart SVG generation: basic, all zeros, all 100s, < 3 dims fallback, custom color/size, XSS safety
- HTML report with radar: section present, escaping, version in footer, comparison section

## 0.5.0 (2026-05-25)

### New Features
- **Docstring coverage scoring**: `compute_docstring_coverage()` — AST-based docstring detection on modules, classes, and functions (9% weight)
- **Type hint coverage scoring**: `compute_type_hint_coverage()` — parameter and return annotation analysis (9% weight)
- **GitHub Actions CI workflow**: `.github/workflows/ci.yml` — multi-Python test matrix (3.10, 3.11, 3.12), ruff lint, mypy check
- **Updated scoring formula**: Rebalanced from 7 factors to 9 factors (100 points total)

### Improvements
- **Scoring breakdown now shows 9 factors** (was 7): includes docstring_coverage and type_hint_coverage
- **Type hints throughout** reporter.py: all variables annotated
- **Reporter breakdown** recalculated to match new scorer weights (25/12/11/11/8/8/7/9/9)

### Tests
- 25 new tests for v0.5.0 features

## 0.4.1 (2026-04-11)

### Bug Fixes
- Fixed 3 failing tests: `--compare` takes 2 separate args (not comma-separated), `Config.get_agent_config()` returns `{}` not `None`, empty model string handled gracefully

### Tests
- 49 new edge case tests (229 total)
- Full coverage: collector, scorer, pricing, config, storage, reporter
