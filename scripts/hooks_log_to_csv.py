#!/usr/bin/env python3
"""Convert Codex hook JSONL logs into CSV files for reporting."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


EVENT_COLUMNS = [
    "line_number",
    "event_timestamp",
    "event_date",
    "event_hour",
    "hook_type",
    "session_id",
    "turn_id",
    "cwd",
    "model",
    "permission_mode",
    "tool_use_id",
    "tool_name",
    "tool_command",
    "prompt",
    "last_assistant_message",
    "cumulative_input_tokens",
    "cumulative_cached_input_tokens",
    "cumulative_output_tokens",
    "cumulative_reasoning_output_tokens",
    "cumulative_total_tokens",
    "latest_input_tokens",
    "latest_cached_input_tokens",
    "latest_output_tokens",
    "latest_reasoning_output_tokens",
    "latest_total_tokens",
    "model_context_window",
    "plan_type",
    "has_credits",
    "transcript_path",
    "raw_payload_json",
    "raw_token_usage_json",
]

TOOL_CALL_COLUMNS = [
    "tool_use_id",
    "session_id",
    "turn_id",
    "tool_name",
    "tool_command",
    "started_at",
    "finished_at",
    "duration_ms",
    "status",
    "response_preview",
    "raw_tool_input_json",
    "raw_tool_response_json",
]

SKILL_INVOCATION_COLUMNS = [
    "session_id",
    "turn_id",
    "skill_name",
    "invoked_at",
    "skill_path",
    "detection_method",
]

SKILL_PATH_PATTERN = re.compile(
    r"(?P<path>(?:[A-Za-z]:)?[\\/]?"
    r"(?:[^\\/\s\"'|;&(),]+[\\/])*"
    r"skills[\\/]"
    r"(?:[^\\/\s\"'|;&(),]+[\\/])*"
    r"[^\\/\s\"'|;&(),]+[\\/]SKILL\.md)",
    re.IGNORECASE,
)

QUOTED_SKILL_PATH_PATTERN = re.compile(
    r"(?P<quote>[\"'])(?P<path>(?:[A-Za-z]:)?[\\/]?"
    r"(?:[^\\/\"']+[\\/])*"
    r"skills[\\/]"
    r"(?:[^\\/\"']+[\\/])*"
    r"[^\\/\"']+[\\/]SKILL\.md)(?P=quote)",
    re.IGNORECASE,
)


def main() -> int:
    workspace_root = default_workspace_root().resolve()
    default_log = default_hooks_log_path(workspace_root).resolve()
    parser = argparse.ArgumentParser(
        description="Convert hooks.log JSONL records into Power BI-friendly CSV files."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=str(default_log),
        help="Path to the hooks JSONL log. Defaults to <workspace>/.codex/hooks.log.",
    )
    parser.add_argument(
        "--events-out",
        default=str(workspace_root / "hooks_events.csv"),
        help="Output path for one-row-per-hook-event CSV.",
    )
    parser.add_argument(
        "--tool-calls-out",
        default=str(workspace_root / "hooks_tool_calls.csv"),
        help="Output path for joined PreToolUse/PostToolUse CSV.",
    )
    parser.add_argument(
        "--skill-invocations-out",
        default=str(workspace_root / "hooks_skill_invocations.csv"),
        help="Output path for skill invocations inferred from tool calls.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    events_out = resolve_workspace_path(workspace_root, Path(args.events_out))
    tool_calls_out = resolve_workspace_path(workspace_root, Path(args.tool_calls_out))
    skill_invocations_out = resolve_workspace_path(
        workspace_root, Path(args.skill_invocations_out)
    )

    records = read_records(input_path)
    write_events_csv(records, events_out)
    write_tool_calls_csv(records, tool_calls_out)
    write_skill_invocations_csv(records, skill_invocations_out)

    print(f"Wrote {len(records)} events to {events_out}", file=sys.stderr)
    print(f"Wrote tool-call rows to {tool_calls_out}", file=sys.stderr)
    print(f"Wrote skill-invocation rows to {skill_invocations_out}", file=sys.stderr)
    return 0


def default_workspace_root() -> Path:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()

    return Path(output)


def default_hooks_log_path(workspace_root: Path) -> Path:
    return workspace_root / ".codex" / "hooks.log"


def resolve_workspace_path(workspace_root: Path, path: Path) -> Path:
    path = path.expanduser()
    candidate = path if path.is_absolute() else workspace_root / path
    resolved = candidate.resolve()
    if resolved == workspace_root or workspace_root in resolved.parents:
        return resolved
    raise SystemExit(f"Refusing to use path outside the workspace: {path}")


def read_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                # The log may be read while another process is appending a line.
                continue
            record["_line_number"] = line_number
            records.append(record)
    return records


def write_events_csv(records: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=EVENT_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(event_row(record))


def write_tool_calls_csv(records: list[dict[str, Any]], path: Path) -> None:
    starts: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    for record in records:
        payload = record.get("payload") or {}
        tool_use_id = payload.get("tool_use_id")
        if not tool_use_id:
            continue

        hook_type = record.get("hook_type")
        if hook_type == "PreToolUse":
            starts[tool_use_id] = record
        elif hook_type == "PostToolUse":
            start = starts.pop(tool_use_id, None)
            rows.append(tool_call_row(start, record))

    for start in starts.values():
        rows.append(tool_call_row(start, None))

    rows.sort(key=lambda row: row["started_at"] or row["finished_at"])

    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=TOOL_CALL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_skill_invocations_csv(
    records: list[dict[str, Any]], path: Path
) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SKILL_INVOCATION_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerows(skill_invocation_rows(record))


def skill_invocation_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    if record.get("hook_type") != "PreToolUse":
        return []

    payload = record.get("payload") or {}
    if str(payload.get("tool_name", "")).casefold() == "apply_patch":
        return []

    tool_input = payload.get("tool_input") or {}
    skill_paths = {
        skill_path
        for value in string_values(tool_input)
        for skill_path in skill_paths_in_text(value)
    }

    return [
        {
            "session_id": payload.get("session_id"),
            "turn_id": payload.get("turn_id"),
            "skill_name": re.split(r"[\\/]", skill_path)[-2],
            "invoked_at": record.get("timestamp"),
            "skill_path": skill_path,
            "detection_method": "skill_path_in_tool_input",
        }
        for skill_path in sorted(skill_paths)
    ]


def skill_paths_in_text(value: str) -> set[str]:
    quoted_paths = {
        match.group("path") for match in QUOTED_SKILL_PATH_PATTERN.finditer(value)
    }
    unquoted_paths = {
        match.group("path") for match in SKILL_PATH_PATTERN.finditer(value)
    }
    suffixes_of_quoted_paths = {
        path
        for path in unquoted_paths
        if any(quoted_path.endswith(path) for quoted_path in quoted_paths)
    }
    return quoted_paths | (unquoted_paths - suffixes_of_quoted_paths)


def string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in string_values(item)]
    if isinstance(value, list):
        return [text for item in value for text in string_values(item)]
    return []


def event_row(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload") or {}
    token_usage = record.get("token_usage") or {}
    cumulative = token_usage.get("cumulative") or {}
    latest = token_usage.get("latest_completed_model_call") or {}
    rate_limits = token_usage.get("rate_limits") or {}
    credits = rate_limits.get("credits") or {}
    timestamp = record.get("timestamp")
    parsed_timestamp = parse_timestamp(timestamp)
    tool_input = payload.get("tool_input") or {}

    return {
        "line_number": record.get("_line_number"),
        "event_timestamp": timestamp,
        "event_date": parsed_timestamp.date().isoformat() if parsed_timestamp else "",
        "event_hour": parsed_timestamp.hour if parsed_timestamp else "",
        "hook_type": record.get("hook_type"),
        "session_id": payload.get("session_id"),
        "turn_id": payload.get("turn_id"),
        "cwd": payload.get("cwd"),
        "model": payload.get("model"),
        "permission_mode": payload.get("permission_mode"),
        "tool_use_id": payload.get("tool_use_id"),
        "tool_name": payload.get("tool_name"),
        "tool_command": tool_input.get("command") if isinstance(tool_input, dict) else "",
        "prompt": payload.get("prompt"),
        "last_assistant_message": payload.get("last_assistant_message"),
        "cumulative_input_tokens": cumulative.get("input_tokens"),
        "cumulative_cached_input_tokens": cumulative.get("cached_input_tokens"),
        "cumulative_output_tokens": cumulative.get("output_tokens"),
        "cumulative_reasoning_output_tokens": cumulative.get("reasoning_output_tokens"),
        "cumulative_total_tokens": cumulative.get("total_tokens"),
        "latest_input_tokens": latest.get("input_tokens"),
        "latest_cached_input_tokens": latest.get("cached_input_tokens"),
        "latest_output_tokens": latest.get("output_tokens"),
        "latest_reasoning_output_tokens": latest.get("reasoning_output_tokens"),
        "latest_total_tokens": latest.get("total_tokens"),
        "model_context_window": token_usage.get("model_context_window"),
        "plan_type": rate_limits.get("plan_type"),
        "has_credits": credits.get("has_credits"),
        "transcript_path": payload.get("transcript_path"),
        "raw_payload_json": compact_json(payload),
        "raw_token_usage_json": compact_json(token_usage),
    }


def tool_call_row(
    start: dict[str, Any] | None, finish: dict[str, Any] | None
) -> dict[str, Any]:
    base = finish or start or {}
    start_payload = (start or {}).get("payload") or {}
    finish_payload = (finish or {}).get("payload") or {}
    payload = finish_payload or start_payload
    tool_input = payload.get("tool_input") or start_payload.get("tool_input") or {}
    tool_response = finish_payload.get("tool_response")
    started_at = (start or {}).get("timestamp")
    finished_at = (finish or {}).get("timestamp")

    return {
        "tool_use_id": payload.get("tool_use_id"),
        "session_id": payload.get("session_id"),
        "turn_id": payload.get("turn_id"),
        "tool_name": payload.get("tool_name"),
        "tool_command": tool_input.get("command") if isinstance(tool_input, dict) else "",
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms(started_at, finished_at),
        "status": "completed" if finish else "started",
        "response_preview": response_preview(tool_response),
        "raw_tool_input_json": compact_json(tool_input),
        "raw_tool_response_json": compact_json(finish_payload.get("tool_response")),
    }


def duration_ms(started_at: str | None, finished_at: str | None) -> int | str:
    start = parse_timestamp(started_at)
    finish = parse_timestamp(finished_at)
    if not start or not finish:
        return ""
    return round((finish - start).total_seconds() * 1000)


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def response_preview(value: Any, max_length: int = 500) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = compact_json(value)
    text = " ".join(text.split())
    return text[:max_length]


def compact_json(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    raise SystemExit(main())
