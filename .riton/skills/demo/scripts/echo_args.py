"""Demo script that echoes serialized sandbox arguments."""

from __future__ import annotations

import json
import sys


def main() -> int:
    """Parse the first argument as JSON and print a compact summary."""
    if len(sys.argv) < 2:
        print("Missing JSON args payload", file=sys.stderr)
        return 2

    payload = json.loads(sys.argv[1])
    print(f"echo_args: {json.dumps(payload, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
