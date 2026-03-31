"""Tests for tablevectorize text utility functions."""

import pytest

from src.modules.tablevectorize.service.tablevectorize_text_utils import (
    clean_text,
    is_meaningless_short_text,
    split_text_by_char_limit,
)


def test_clean_text_normalizes_whitespace() -> None:
    """Ensure whitespace is collapsed and surrounding spaces are trimmed."""
    content: str = "  hello\n\t  world   from\r\n tablevectorize  "

    assert clean_text(content) == "hello world from tablevectorize"


def test_is_meaningless_short_text_identifies_short_content() -> None:
    """Ensure very short text is considered meaningless."""
    assert is_meaningless_short_text("111") is True
    assert is_meaningless_short_text("好评") is True


def test_is_meaningless_short_text_threshold_after_normalization() -> None:
    """Ensure threshold is based on cleaned length (<=3 True, >=4 False)."""
    assert is_meaningless_short_text("  a\n b\t") is True
    assert is_meaningless_short_text(" a\n bc ") is False


def test_is_meaningless_short_text_keeps_meaningful_sentence() -> None:
    """Ensure a meaningful sentence is not marked as meaningless."""
    assert is_meaningless_short_text("This shop has great value and service.") is False


def test_split_text_by_char_limit_creates_expected_chunks() -> None:
    """Ensure content splits into chunk sizes [500, 500, 201]."""
    content: str = "a" * 1201

    chunks: list[str] = split_text_by_char_limit(content, max_chars=500)

    assert len(chunks) == 3
    assert [len(chunk) for chunk in chunks] == [500, 500, 201]


def test_split_text_by_char_limit_rejects_non_positive_max_chars() -> None:
    """Ensure non-positive max_chars raises ValueError."""
    content: str = "hello"

    with pytest.raises(ValueError, match="max_chars must be greater than 0"):
        split_text_by_char_limit(content, max_chars=0)


def test_split_text_by_char_limit_returns_empty_for_blank_input() -> None:
    """Ensure empty or whitespace-only content yields no chunks."""
    assert split_text_by_char_limit("", max_chars=10) == []
    assert split_text_by_char_limit("  \n\t  ", max_chars=10) == []
