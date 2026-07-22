#!/usr/bin/env python3
"""Append Codex hook invocations to the current workspace's JSONL log."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Iterator

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def log_path() -> Path:
    """Return the platform-appropriate log destination."""
    if sys.platform == "win32":
        return Path.home() / ".codex" / "hooks.log"

    try:
        workspace_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd() / "hooks.log"

    return Path(workspace_root) / "hooks.log"


def read_payload() -> object:
    characters = []
    depth = 0
    in_string = False
    escaped = False
    started = False

    while character := sys.stdin.read(1):
        characters.append(character)

        if not started:
            if character.isspace():
                continue
            if character not in "[{":
                characters.append(sys.stdin.read())
                break
            started = True
            depth = 1
            continue

        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
        elif character in "]}":
            depth -= 1
            if depth == 0:
                break

    raw_payload = "".join(characters)
    if not raw_payload:
        return None

    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError:
        return raw_payload


@contextmanager
def exclusive_file_lock(log_file: IO[str]) -> Iterator[None]:
    if os.name == "nt":
        position = log_file.tell()
        log_file.seek(0)
        msvcrt.locking(log_file.fileno(), msvcrt.LK_LOCK, 1)
        try:
            log_file.seek(position)
            yield
        finally:
            log_file.seek(0)
            msvcrt.locking(log_file.fileno(), msvcrt.LK_UNLCK, 1)
            log_file.seek(position)
        return

    fcntl.flock(log_file.fileno(), fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(log_file.fileno(), fcntl.LOCK_UN)


def latest_token_usage(payload: object) -> dict:
    empty_usage = {
        "cumulative": None,
        "latest_completed_model_call": None,
        "model_context_window": None,
        "reasoning_effort": None,
        "rate_limits": None,
        "source": None,
    }

    if not isinstance(payload, dict):
        return empty_usage

    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path:
        return empty_usage

    source = {
        "transcript_path": transcript_path,
        "token_count_timestamp": None,
    }

    try:
        transcript = Path(transcript_path)
        last_token_count = None
        current_reasoning_effort = None
        last_reasoning_effort = None
        with transcript.open("r", encoding="utf-8") as transcript_file:
            for line in transcript_file:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_payload = event.get("payload")
                if not isinstance(event_payload, dict):
                    continue

                event_reasoning_effort = reasoning_effort(event_payload)
                if event_reasoning_effort:
                    current_reasoning_effort = event_reasoning_effort

                if event_payload.get("type") == "token_count":
                    last_token_count = event
                    last_reasoning_effort = current_reasoning_effort
    except OSError as error:
        return {
            **empty_usage,
            "source": {
                **source,
                "error": str(error),
            },
        }

    if last_token_count is None:
        return {
            **empty_usage,
            "source": source,
        }

    source["token_count_timestamp"] = last_token_count.get("timestamp")
    token_payload = last_token_count.get("payload", {})
    info = token_payload.get("info", {})

    if not isinstance(info, dict):
        return {
            **empty_usage,
            "source": source,
        }

    return {
        "cumulative": info.get("total_token_usage"),
        "latest_completed_model_call": info.get("last_token_usage"),
        "model_context_window": info.get("model_context_window"),
        "reasoning_effort": last_reasoning_effort,
        "rate_limits": token_payload.get("rate_limits"),
        "source": source,
    }


def reasoning_effort(payload: dict) -> str | None:
    thread_settings = payload.get("thread_settings") or {}
    collaboration_mode = payload.get("collaboration_mode") or {}
    collaboration_settings = collaboration_mode.get("settings") or {}
    candidates = (
        payload.get("reasoning_effort"),
        thread_settings.get("reasoning_effort"),
        collaboration_settings.get("reasoning_effort"),
    )
    return next(
        (value for value in candidates if isinstance(value, str) and value), None
    )


def main() -> int:
    hook_type = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    payload = read_payload()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hook_type": hook_type,
        "payload": payload,
        "token_usage": latest_token_usage(payload),
    }

    destination = log_path()
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("a", encoding="utf-8") as log_file:
        with exclusive_file_lock(log_file):
            log_file.write(json.dumps(record, sort_keys=True) + "\n")
            log_file.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
