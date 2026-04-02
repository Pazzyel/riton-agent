"""Skill whitelist configuration for sandbox execution."""

import os


_DEFAULT_ALLOWED_SKILLS: set[str] = {
    "demo",
    "shell-script",
    "python-script",
}


def get_allowed_skills() -> set[str]:
    """Return allowed skill names with optional environment override."""
    raw_override = os.getenv("RITON_ALLOWED_SKILLS")
    if raw_override is None:
        return set(_DEFAULT_ALLOWED_SKILLS)

    # Parse a simple comma-separated override to keep extension points external.
    parsed_values = {
        value.strip()
        for value in raw_override.split(",")
        if value.strip()
    }
    if not parsed_values:
        return set(_DEFAULT_ALLOWED_SKILLS)

    return parsed_values
