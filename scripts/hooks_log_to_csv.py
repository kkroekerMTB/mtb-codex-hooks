#!/usr/bin/env python3
"""Convert Codex hook JSONL logs into CSV files for reporting."""

from __future__ import annotations

import argparse
import csv
import json
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert hooks.log JSONL records into Power BI-friendly CSV files."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="hooks.log",
        help="Path to the hooks JSONL log. Defaults to hooks.log.",
    )
    parser.add_argument(
        "--events-out",
        default="hooks_events.csv",
        help="Output path for one-row-per-hook-event CSV.",
    )
    parser.add_argument(
        "--tool-calls-out",
        default="hooks_tool_calls.csv",
        help="Output path for joined PreToolUse/PostToolUse CSV.",
    )
    args = parser.parse_args()

    records = read_records(Path(args.input))
    write_events_csv(records, Path(args.events_out))
    write_tool_calls_csv(records, Path(args.tool_calls_out))

    print(f"Wrote {len(records)} events to {args.events_out}")
    print(f"Wrote tool-call rows to {args.tool_calls_out}")
    return 0


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
