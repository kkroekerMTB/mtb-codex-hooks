#!/usr/bin/env python3
"""Append Codex hook invocations to a shared JSONL log."""

from __future__ import annotations

import json
import os
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
    configured_path = os.environ.get("CODEX_HOOKS_LOG_PATH")
    if configured_path:
        return Path(configured_path).expanduser()

    return Path.home() / ".codex" / "hooks.log"


def read_payload() -> object:
    raw_payload = sys.stdin.read()
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
        with transcript.open("r", encoding="utf-8") as transcript_file:
            for line in transcript_file:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_payload = event.get("payload")
                if not isinstance(event_payload, dict):
                    continue

                if event_payload.get("type") == "token_count":
                    last_token_count = event
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
        "rate_limits": token_payload.get("rate_limits"),
        "source": source,
    }


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
