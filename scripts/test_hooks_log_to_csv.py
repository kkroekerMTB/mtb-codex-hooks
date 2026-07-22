from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hooks_log_to_csv


class HooksLogToCsvTest(unittest.TestCase):
    def test_default_workspace_root_falls_back_to_cwd_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with mock.patch("subprocess.check_output", side_effect=OSError):
                with mock.patch("pathlib.Path.cwd", return_value=temp_path):
                    self.assertEqual(temp_path, hooks_log_to_csv.default_workspace_root())

    def test_resolve_workspace_path_rejects_paths_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir).resolve()
            with self.assertRaises(SystemExit):
                hooks_log_to_csv.resolve_workspace_path(
                    workspace_root, Path("/tmp/elsewhere/hooks.log")
                )

    def test_main_uses_workspace_codex_hooks_log_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            workspace_root = temp_path / "workspace"
            workspace_root.mkdir()
            codex_dir = workspace_root / ".codex"
            log_path = codex_dir / "hooks.log"
            events_path = workspace_root / "hooks_events.csv"
            tool_calls_path = workspace_root / "hooks_tool_calls.csv"
            skill_invocations_path = workspace_root / "hooks_skill_invocations.csv"
            codex_dir.mkdir()
            log_path.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-06-30T15:05:58.563649+00:00",
                        "hook_type": "Stop",
                        "payload": {
                            "session_id": "session-1",
                            "turn_id": "turn-1",
                            "last_assistant_message": "done",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            old_argv = sys.argv
            stdout = io.StringIO()
            stderr = io.StringIO()
            try:
                with mock.patch(
                    "hooks_log_to_csv.default_workspace_root", return_value=workspace_root
                ):
                    sys.argv = [
                        "hooks_log_to_csv.py",
                        "--events-out",
                        str(events_path),
                        "--tool-calls-out",
                        str(tool_calls_path),
                    ]

                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        exit_code = hooks_log_to_csv.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(0, exit_code)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("Wrote 1 events", stderr.getvalue())
            self.assertTrue(events_path.exists())
            self.assertTrue(tool_calls_path.exists())
            self.assertTrue(skill_invocations_path.exists())

    def test_main_exports_skill_invocations_inferred_from_tool_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            workspace_root.mkdir()
            codex_dir = workspace_root / ".codex"
            codex_dir.mkdir()
            (codex_dir / "hooks.log").write_text(
                json.dumps(
                    {
                        "timestamp": "2026-07-22T15:05:58.563649+00:00",
                        "hook_type": "PreToolUse",
                        "payload": {
                            "session_id": "session-1",
                            "turn_id": "turn-1",
                            "tool_name": "Bash",
                            "tool_use_id": "tool-1",
                            "tool_input": {
                                "command": (
                                    "sed -n '1,260p' "
                                    "/home/user/.codex/skills/implement/SKILL.md"
                                )
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            old_argv = sys.argv
            try:
                with mock.patch(
                    "hooks_log_to_csv.default_workspace_root", return_value=workspace_root
                ):
                    sys.argv = ["hooks_log_to_csv.py"]
                    with redirect_stderr(io.StringIO()):
                        exit_code = hooks_log_to_csv.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(0, exit_code)
            with (workspace_root / "hooks_skill_invocations.csv").open(
                encoding="utf-8", newline=""
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual(
                [
                    {
                        "session_id": "session-1",
                        "turn_id": "turn-1",
                        "skill_name": "implement",
                        "invoked_at": "2026-07-22T15:05:58.563649+00:00",
                        "skill_path": "/home/user/.codex/skills/implement/SKILL.md",
                        "detection_method": "skill_path_in_tool_input",
                    }
                ],
                rows,
            )

    def test_skill_invocations_support_windows_skill_paths(self) -> None:
        record = {
            "timestamp": "2026-07-22T15:05:58+00:00",
            "hook_type": "PreToolUse",
            "payload": {
                "session_id": "session-1",
                "turn_id": "turn-1",
                "tool_input": {
                    "file_path": r"C:\Users\me\.codex\skills\openai-docs\SKILL.md"
                },
            },
        }

        rows = hooks_log_to_csv.skill_invocation_rows(record)

        self.assertEqual("openai-docs", rows[0]["skill_name"])
        self.assertEqual(
            r"C:\Users\me\.codex\skills\openai-docs\SKILL.md",
            rows[0]["skill_path"],
        )

    def test_skill_invocations_preserve_quoted_paths_containing_spaces(self) -> None:
        record = {
            "timestamp": "2026-07-22T15:05:58+00:00",
            "hook_type": "PreToolUse",
            "payload": {
                "tool_input": {
                    "command": (
                        "sed -n '1,260p' "
                        "'/home/Some User/.codex/skills/implement/SKILL.md'"
                    )
                }
            },
        }

        rows = hooks_log_to_csv.skill_invocation_rows(record)

        self.assertEqual(
            "/home/Some User/.codex/skills/implement/SKILL.md",
            rows[0]["skill_path"],
        )

    def test_skill_invocations_count_each_skill_once_per_pre_tool_call(self) -> None:
        skill_path = "/home/user/.codex/skills/implement/SKILL.md"
        pre_tool_use = {
            "timestamp": "2026-07-22T15:05:58+00:00",
            "hook_type": "PreToolUse",
            "payload": {
                "tool_input": {"command": f"sed -n '1,20p' {skill_path} {skill_path}"}
            },
        }
        post_tool_use = {
            **pre_tool_use,
            "hook_type": "PostToolUse",
        }

        rows = hooks_log_to_csv.skill_invocation_rows(
            pre_tool_use
        ) + hooks_log_to_csv.skill_invocation_rows(post_tool_use)

        self.assertEqual(1, len(rows))

    def test_skill_invocations_ignore_skill_paths_in_patch_content(self) -> None:
        record = {
            "timestamp": "2026-07-22T15:05:58+00:00",
            "hook_type": "PreToolUse",
            "payload": {
                "tool_name": "apply_patch",
                "tool_input": {
                    "command": (
                        "*** Begin Patch\n"
                        "+/home/user/.codex/skills/implement/SKILL.md\n"
                        "*** End Patch"
                    )
                },
            },
        }

        self.assertEqual([], hooks_log_to_csv.skill_invocation_rows(record))


if __name__ == "__main__":
    unittest.main()
