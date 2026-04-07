"""Tests for collector module."""

from agent_bench.collector import parse_tokens, parse_test_results, parse_lint_results, collect_from_output


class TestParseTokens:
    def test_claude_format(self):
        inp, out = parse_tokens("Token usage: 15000 input, 8000 output")
        assert inp == 15000
        assert out == 8000

    def test_generic_format(self):
        inp, out = parse_tokens("5000 input tokens, 3000 output tokens")
        assert inp == 5000
        assert out == 3000

    def test_comma_numbers(self):
        inp, out = parse_tokens("Usage: 1,500 input, 2,300 output")
        assert inp == 1500
        assert out == 2300

    def test_no_match(self):
        inp, out = parse_tokens("no token info here")
        assert inp == 0
        assert out == 0

    def test_empty_string(self):
        inp, out = parse_tokens("")
        assert inp == 0


class TestParseTestResults:
    def test_pytest_passed(self):
        p, t = parse_test_results("5 passed")
        assert p == 5
        assert t == 5

    def test_pytest_passed_failed(self):
        p, t = parse_test_results("3 passed, 2 failed")
        assert p == 3
        assert t == 5

    def test_pytest_with_errors(self):
        p, t = parse_test_results("3 passed, 1 error")
        assert p == 3
        assert t == 4

    def test_no_tests(self):
        p, t = parse_test_results("no tests ran")
        assert p == 0
        assert t == 0

    def test_empty(self):
        p, t = parse_test_results("")
        assert p == 0


class TestParseLintResults:
    def test_ruff_errors(self):
        errs, warns = parse_lint_results("file.py:1:1: E501 line too long\nfile.py:2:1: E302 expected blank line")
        assert errs == 2

    def test_mixed(self):
        errs, warns = parse_lint_results("file.py:1:1: W291 trailing whitespace\nfile.py:2:1: E501 line too long")
        assert errs == 1
        assert warns == 1

    def test_summary_format(self):
        errs, warns = parse_lint_results("3 errors, 1 warning")
        assert errs == 3
        assert warns == 1

    def test_clean(self):
        errs, warns = parse_lint_results("All checks passed!")
        assert errs == 0
        assert warns == 0


class TestCollectFromOutput:
    def test_basic_collection(self):
        m = collect_from_output("done", "", 0, 45.0)
        assert m.exit_code == 0
        assert m.duration_seconds == 45.0

    def test_with_test_output(self):
        m = collect_from_output("done", "", 0, 10.0, test_output="8 passed")
        assert m.test_pass == 8
        assert m.test_total == 8

    def test_with_lint_output(self):
        m = collect_from_output("done", "", 0, 10.0, lint_output="2 errors, 1 warning")
        assert m.lint_errors == 2
        assert m.lint_warnings == 1

    def test_with_tokens(self):
        m = collect_from_output("Usage: 1000 input, 500 output", "", 0, 10.0)
        assert m.tokens_in == 1000
        assert m.tokens_out == 500

    def test_nonzero_exit(self):
        m = collect_from_output("error", "failed", 1, 5.0)
        assert m.exit_code == 1
