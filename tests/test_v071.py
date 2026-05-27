"""Tests for v0.7.1 improvements: expanded detector, collector patterns, storage methods."""

import re
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agent_bench.collector import parse_tokens, TOKEN_PATTERNS
from agent_bench.detector import KNOWN_AGENTS, BINARY_MAP, detect_agent
from agent_bench.storage import Storage


class TestExpandedDetector:
    """Tests for newly added agents in detector."""

    def test_cursor_in_known_agents(self):
        assert "cursor" in KNOWN_AGENTS

    def test_kiro_in_known_agents(self):
        assert "kiro" in KNOWN_AGENTS

    def test_auggie_in_known_agents(self):
        assert "auggie" in KNOWN_AGENTS

    def test_goose_in_known_agents(self):
        assert "goose" in KNOWN_AGENTS

    def test_cursor_binary_map(self):
        assert BINARY_MAP["cursor"] == "cursor"

    def test_kiro_binary_map(self):
        assert BINARY_MAP["kiro"] == "kiro"

    def test_auggie_binary_map(self):
        assert BINARY_MAP["auggie"] == "auggie"

    def test_goose_binary_map(self):
        assert BINARY_MAP["goose"] == "goose"

    def test_total_agent_count(self):
        # Should have at least 11 agents now
        assert len(KNOWN_AGENTS) >= 11

    @patch("shutil.which", return_value=None)
    def test_detect_new_agent_not_installed(self, mock_which):
        info = detect_agent("cursor")
        assert info.name == "cursor"
        assert not info.installed


class TestExpandedTokenPatterns:
    """Tests for new token parsing patterns."""

    def test_codex_format(self):
        """Codex CLI: 'Tokens: 1234 in / 5678 out'"""
        result = parse_tokens("Tokens: 1234 in / 5678 out")
        assert result == (1234, 5678)

    def test_gemini_multiline(self):
        """Gemini: 'Input tokens: 1234\nOutput tokens: 5678'"""
        result = parse_tokens("Input tokens: 1234\nOutput tokens: 5678")
        assert result == (1234, 5678)

    def test_openai_api_format(self):
        """OpenAI API: 'prompt_tokens: 100, completion_tokens: 200'"""
        result = parse_tokens("prompt_tokens: 100, completion_tokens: 200")
        assert result == (100, 200)

    def test_anthropic_api_format(self):
        """Anthropic: 'input_tokens: 500, output_tokens: 300'"""
        result = parse_tokens("input_tokens: 500, output_tokens: 300")
        assert result == (500, 300)

    def test_compact_format(self):
        """Compact: '500in/300out'"""
        result = parse_tokens("500in/300out")
        assert result == (500, 300)

    def test_compact_space_format(self):
        """Compact: '500 in 300 out'"""
        result = parse_tokens("500 in 300 out")
        assert result == (500, 300)

    def test_comma_separated_numbers(self):
        """Numbers with commas: '1,234 input, 5,678 output'"""
        result = parse_tokens("1,234 input, 5,678 output")
        assert result == (1234, 5678)

    def test_no_tokens_found(self):
        result = parse_tokens("no token info here")
        assert result == (0, 0)

    def test_original_claude_format(self):
        """Original format still works: 'Token usage: 1000 input, 2000 output'"""
        result = parse_tokens("Token usage: 1000 input, 2000 output")
        assert result == (1000, 2000)

    def test_token_patterns_are_valid_regex(self):
        """All token patterns compile and match correctly."""
        for pattern in TOKEN_PATTERNS:
            assert isinstance(pattern, re.Pattern)


class TestStorageNewMethods:
    """Tests for new storage utility methods."""

    def _make_storage(self) -> Storage:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        storage = Storage(path=Path(tmp.name))
        return storage

    def test_get_all_agent_names_empty(self):
        storage = self._make_storage()
        names = storage.get_all_agent_names()
        assert names == []
        storage.close()

    def test_get_all_agent_names_with_data(self):
        storage = self._make_storage()
        storage.save_run("run1", "task1", [
            {"agent_name": "claude-code", "quality_score": 85.0, "quality_grade": "B"},
            {"agent_name": "codex-cli", "quality_score": 90.0, "quality_grade": "A"},
        ])
        storage.save_run("run2", "task2", [
            {"agent_name": "claude-code", "quality_score": 88.0, "quality_grade": "B+"},
            {"agent_name": "gemini-cli", "quality_score": 75.0, "quality_grade": "C"},
        ])
        names = storage.get_all_agent_names()
        assert names == ["claude-code", "codex-cli", "gemini-cli"]
        storage.close()

    def test_get_run_count_empty(self):
        storage = self._make_storage()
        assert storage.get_run_count() == 0
        storage.close()

    def test_get_run_count_with_data(self):
        storage = self._make_storage()
        storage.save_run("run1", "task1", [{"agent_name": "a"}])
        storage.save_run("run2", "task2", [{"agent_name": "b"}])
        storage.save_run("run3", "task3", [{"agent_name": "c"}])
        assert storage.get_run_count() == 3
        storage.close()

    def test_get_agent_stats_no_data(self):
        storage = self._make_storage()
        stats = storage.get_agent_stats("nonexistent")
        assert stats["run_count"] == 0
        assert stats["agent_name"] == "nonexistent"
        storage.close()

    def test_get_agent_stats_with_data(self):
        storage = self._make_storage()
        storage.save_run("run1", "task1", [
            {
                "agent_name": "claude-code",
                "quality_score": 80.0,
                "quality_grade": "B",
                "duration_seconds": 10.0,
                "tokens_in": 1000,
                "tokens_out": 500,
                "cost": 0.05,
                "test_pass": 8,
                "test_total": 10,
            },
        ])
        storage.save_run("run2", "task2", [
            {
                "agent_name": "claude-code",
                "quality_score": 90.0,
                "quality_grade": "A",
                "duration_seconds": 20.0,
                "tokens_in": 2000,
                "tokens_out": 1000,
                "cost": 0.10,
                "test_pass": 10,
                "test_total": 10,
            },
        ])
        stats = storage.get_agent_stats("claude-code")
        assert stats["run_count"] == 2
        assert stats["avg_score"] == 85.0
        assert stats["best_score"] == 90.0
        assert stats["worst_score"] == 80.0
        assert stats["avg_duration"] == 15.0
        assert stats["total_tokens_in"] == 3000
        assert stats["total_tokens_out"] == 1500
        assert stats["total_cost"] == 0.15
        assert stats["total_tests_passed"] == 18
        assert stats["total_tests_run"] == 20
        storage.close()

    def test_get_agent_stats_ignores_other_agents(self):
        storage = self._make_storage()
        storage.save_run("run1", "task1", [
            {"agent_name": "claude-code", "quality_score": 80.0, "quality_grade": "B"},
            {"agent_name": "codex-cli", "quality_score": 90.0, "quality_grade": "A"},
        ])
        stats = storage.get_agent_stats("claude-code")
        assert stats["run_count"] == 1
        assert stats["avg_score"] == 80.0
        storage.close()
