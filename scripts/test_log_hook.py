from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


LOG_HOOK_PATH = Path(__file__).resolve().parents[1] / ".codex" / "hooks" / "log_hook.py"
SPEC = importlib.util.spec_from_file_location("log_hook", LOG_HOOK_PATH)
log_hook = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(log_hook)


class LogHookTest(unittest.TestCase):
    def test_read_payload_handles_nested_json_and_braces_in_strings(self) -> None:
        payload = {
            "tool_input": {
                "command": "python -c 'print({\"status\": \"ok}\")'",
                "items": [1, {"nested": True}],
            }
        }

        with mock.patch.object(log_hook.sys, "stdin", io.StringIO(json.dumps(payload))):
            self.assertEqual(payload, log_hook.read_payload())

    def test_hook_exits_after_one_payload_without_waiting_for_stdin_eof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            hooks_dir = Path(temp_dir) / ".codex" / "hooks"
            hooks_dir.mkdir(parents=True)
            hook_path = hooks_dir / "log_hook.py"
            shutil.copy2(LOG_HOOK_PATH, hook_path)

            process = subprocess.Popen(
                [sys.executable, str(hook_path), "SessionStart"],
                stdin=subprocess.PIPE,
                text=True,
            )
            try:
                assert process.stdin is not None
                process.stdin.write('{"session_id": "session-1"}')
                process.stdin.flush()

                self.assertEqual(0, process.wait(timeout=5))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                if process.stdin is not None:
                    process.stdin.close()

    def test_log_path_uses_codex_directory_containing_hook_script(self) -> None:
        self.assertEqual(
            LOG_HOOK_PATH.parent.parent / "hooks.log",
            log_hook.log_path(),
        )

    def test_latest_token_usage_includes_reasoning_effort_for_latest_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            transcript_path = Path(temp_dir) / "transcript.jsonl"
            events = [
                {
                    "timestamp": "2026-07-22T15:05:57+00:00",
                    "type": "turn_context",
                    "payload": {
                        "collaboration_mode": {
                            "settings": {"reasoning_effort": "high"}
                        }
                    },
                },
                {
                    "timestamp": "2026-07-22T15:05:58+00:00",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "last_token_usage": {"input_tokens": 10},
                            "total_token_usage": {"input_tokens": 10},
                        },
                    },
                },
            ]
            transcript_path.write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )

            usage = log_hook.latest_token_usage(
                {"transcript_path": str(transcript_path)}
            )

            self.assertEqual("high", usage["reasoning_effort"])


if __name__ == "__main__":
    unittest.main()
