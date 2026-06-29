#!/usr/bin/env python3
"""Append Codex hook invocations to hooks.log as JSON lines."""

from __future__ import annotations

import fcntl
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def git_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()

    return Path(result.stdout.strip())


def read_payload() -> object:
    raw_payload = sys.stdin.read()
    if not raw_payload:
        return None

    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError:
        return raw_payload


def main() -> int:
    hook_type = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hook_type": hook_type,
        "payload": read_payload(),
    }

    log_path = git_root() / "hooks.log"
    with log_path.open("a", encoding="utf-8") as log_file:
        fcntl.flock(log_file.fileno(), fcntl.LOCK_EX)
        log_file.write(json.dumps(record, sort_keys=True) + "\n")
        log_file.flush()
        fcntl.flock(log_file.fileno(), fcntl.LOCK_UN)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
