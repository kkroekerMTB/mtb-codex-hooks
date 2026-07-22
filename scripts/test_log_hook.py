from __future__ import annotations

import importlib.util
import io
import json
import os
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
            workspace_root = Path(temp_dir)
            hooks_dir = workspace_root / ".codex" / "hooks"
            hooks_dir.mkdir(parents=True)
            hook_path = hooks_dir / "log_hook.py"
            shutil.copy2(LOG_HOOK_PATH, hook_path)

            process = subprocess.Popen(
                [sys.executable, str(hook_path), "SessionStart"],
                stdin=subprocess.PIPE,
                text=True,
                cwd=workspace_root,
                env={
                    **os.environ,
                    "HOME": temp_dir,
                    "USERPROFILE": temp_dir,
                },
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

    def test_log_path_uses_git_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            nested_dir = workspace_root / "src" / "nested"
            nested_dir.mkdir(parents=True)
            subprocess.run(["git", "init", "--quiet"], cwd=workspace_root, check=True)

            with mock.patch.object(log_hook.sys, "platform", "linux"):
                with mock.patch.object(log_hook.Path, "cwd", return_value=nested_dir):
                    with mock.patch.object(
                        log_hook.subprocess,
                        "check_output",
                        return_value=str(workspace_root),
                    ):
                        self.assertEqual(
                            workspace_root / "hooks.log", log_hook.log_path()
                        )

    def test_log_path_falls_back_to_current_directory_outside_git(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            workspace_root.mkdir()

            with mock.patch.object(log_hook.sys, "platform", "linux"):
                with mock.patch.object(log_hook.Path, "cwd", return_value=workspace_root):
                    with mock.patch.object(
                        log_hook.subprocess,
                        "check_output",
                        side_effect=subprocess.CalledProcessError(128, "git"),
                    ):
                        self.assertEqual(
                            workspace_root / "hooks.log", log_hook.log_path()
                        )

    def test_log_path_uses_user_codex_directory_on_windows(self) -> None:
        user_home = Path(r"C:\Users\example")

        with mock.patch.object(log_hook.sys, "platform", "win32"):
            with mock.patch.object(log_hook.Path, "home", return_value=user_home):
                self.assertEqual(user_home / ".codex" / "hooks.log", log_hook.log_path())

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
