"""Tests for web reporter radar charts (v0.6.0)."""

from __future__ import annotations

from agent_bench.web_reporter import (
    generate_html,
    _bar_svg,
    _radar_chart_svg,
    _fallback_bar_svg,
    _compute_radar_values,
    RADAR_LABELS,
)


def _sample_run():
    return {
        "run_id": "test-001",
        "task": "Add pagination",
        "timestamp": "2026-05-25T06:00:00",
        "results": [
            {
                "agent_name": "Claude",
                "duration_seconds": 134,
                "cost": 0.42,
                "tokens_in": 18200,
                "tokens_out": 8100,
                "test_pass": 8,
                "test_total": 10,
                "quality_score": 92,
                "quality_grade": "A",
                "exit_code": 0,
                "files_changed": 3,
                "lines_added": 30,
                "lines_removed": 5,
                "lint_errors": 0,
                "lint_warnings": 0,
                "stdout": '"""Module."""\ndef foo():\n    """Do foo."""\n    return 1\n',
                "stderr": "",
            },
            {
                "agent_name": "Codex",
                "duration_seconds": 107,
                "cost": 0.31,
                "tokens_in": 14100,
                "tokens_out": 6200,
                "test_pass": 8,
                "test_total": 8,
                "quality_score": 88,
                "quality_grade": "A-",
                "exit_code": 0,
                "files_changed": 2,
                "lines_added": 20,
                "lines_removed": 3,
                "lint_errors": 1,
                "lint_warnings": 0,
                "stdout": "def bar():\n    return 2\n",
                "stderr": "",
            },
        ],
    }


class TestRadarChart:
    def test_radar_svg_basic(self):
        values = [80, 90, 70, 60, 85, 75, 90, 50, 60, 40, 100]
        svg = _radar_chart_svg(values, RADAR_LABELS)
        assert "<svg" in svg
        assert "polygon" in svg

    def test_radar_svg_all_zeros(self):
        values = [0] * 11
        svg = _radar_chart_svg(values, RADAR_LABELS)
        assert "<svg" in svg

    def test_radar_svg_all_100(self):
        values = [100] * 11
        svg = _radar_chart_svg(values, RADAR_LABELS)
        assert "<svg" in svg

    def test_radar_fewer_than_3_dims(self):
        svg = _radar_chart_svg([50, 80], ["A", "B"])
        assert "<svg" in svg
        assert "rect" in svg  # fallback bar chart

    def test_radar_custom_color(self):
        svg = _radar_chart_svg([50] * 11, RADAR_LABELS, color="#FF0000")
        assert "#FF0000" in svg

    def test_radar_custom_size(self):
        svg = _radar_chart_svg([50] * 11, RADAR_LABELS, size=300)
        assert 'width="300"' in svg
        assert 'height="300"' in svg

    def test_radar_no_xss(self):
        svg = _radar_chart_svg([50] * 11, RADAR_LABELS)
        assert "<script>" not in svg


class TestFallbackBarChart:
    def test_basic(self):
        svg = _fallback_bar_svg([50, 80], ["Label A", "Label B"])
        assert "<svg" in svg
        assert "Label A" in svg

    def test_empty(self):
        assert _fallback_bar_svg([], []) == ""


class TestBreakdownValues:
    def test_basic(self):
        r = _sample_run()["results"][0]
        values = _compute_radar_values(r)
        assert len(values) == 11
        assert all(0 <= v <= 100 for v in values)

    def test_perfect_agent(self):
        r = {
            "test_pass": 10, "test_total": 10,
            "lint_errors": 0, "lint_warnings": 0,
            "lines_added": 20, "lines_removed": 5,
            "exit_code": 0,
            "duration_seconds": 20,
            "stdout": '"""Module."""\ndef foo():\n    """Do foo."""\n    # comment\n    return 1\n',
            "stderr": "",
        }
        values = _compute_radar_values(r)
        assert values[0] == 100  # Tests
        assert values[1] == 100  # Lint
        assert values[3] == 100  # Completion
        assert values[4] == 100  # Speed

    def test_label_count_matches(self):
        assert len(RADAR_LABELS) == 11


class TestHTMLReportWithRadar:
    def test_radar_section_in_html(self):
        h = generate_html(_sample_run())
        assert "Scoring Breakdown" in h
        assert "radar" in h.lower() or "polygon" in h

    def test_html_escaping(self):
        data = {
            "run_id": "r",
            "task": "<script>alert('xss')</script>",
            "timestamp": "",
            "results": [
                {
                    "agent_name": "A&B",
                    "duration_seconds": 10, "cost": 0.1,
                    "tokens_in": 100, "tokens_out": 50,
                    "test_pass": 0, "test_total": 0,
                    "quality_score": 50, "quality_grade": "C",
                    "exit_code": 0, "files_changed": 0,
                    "lines_added": 0, "lines_removed": 0,
                    "lint_errors": 0, "lint_warnings": 0,
                    "stdout": "", "stderr": "",
                }
            ],
        }
        h = generate_html(data)
        assert "<script>" not in h

    def test_version_in_footer(self):
        h = generate_html(_sample_run())
        assert "0.6.0" in h

    def test_no_results(self):
        h = generate_html({"task": "t", "results": []})
        assert "No results" in h

    def test_comparison_section(self):
        run = _sample_run()
        baseline = _sample_run()
        baseline["run_id"] = "baseline-001"
        h = generate_html(run, baseline)
        assert "Comparison" in h
