"""Text utility helpers for table vectorization workflows."""

import re


def clean_text(content: str) -> str:
    """Normalize whitespace and trim leading or trailing spaces."""
    normalized: str = re.sub(r"\s+", " ", content)
    return normalized.strip()


def is_meaningless_short_text(content: str) -> bool:
    """Return True when normalized content is empty or has length <= 3."""
    cleaned_content: str = clean_text(content)
    if not cleaned_content:
        return True
    if len(cleaned_content) <= 3:
        return True
    return False


def split_text_by_char_limit(content: str, max_chars: int) -> list[str]:
    """Split content into fixed-size character chunks by max_chars."""
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")

    cleaned_content: str = clean_text(content)
    if not cleaned_content:
        return []

    chunks: list[str] = []
    for index in range(0, len(cleaned_content), max_chars):
        chunks.append(cleaned_content[index:index + max_chars])
    return chunks
