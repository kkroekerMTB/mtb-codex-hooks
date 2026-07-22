#!/usr/bin/env python3
"""Remove the workspace hook log and its generated CSV reports."""

from __future__ import annotations

from pathlib import Path

from hooks_log_to_csv import (
    EVENTS_CSV_FILENAME,
    MODEL_CALLS_CSV_FILENAME,
    SKILL_INVOCATIONS_CSV_FILENAME,
    TOOL_CALLS_CSV_FILENAME,
    default_workspace_root,
)

DERIVED_CSV_FILENAMES = (
    EVENTS_CSV_FILENAME,
    TOOL_CALLS_CSV_FILENAME,
    SKILL_INVOCATIONS_CSV_FILENAME,
    MODEL_CALLS_CSV_FILENAME,
)


def main() -> int:
    workspace_root = default_workspace_root().resolve()
    removed_count = clear_hooks_log(workspace_root)
    print(f"Removed {removed_count} files from {workspace_root}")
    return 0


def clear_hooks_log(workspace_root: Path) -> int:
    targets = [
        workspace_root / ".codex" / "hooks.log",
        *(workspace_root / filename for filename in DERIVED_CSV_FILENAMES),
    ]
    removed_count = 0
    for target in targets:
        try:
            target.unlink()
        except FileNotFoundError:
            continue
        removed_count += 1

    return removed_count


if __name__ == "__main__":
    raise SystemExit(main())
