from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
