from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clear_hooks_log


class ClearHooksLogTest(unittest.TestCase):
    def test_main_removes_log_and_derived_csv_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            codex_dir = workspace_root / ".codex"
            codex_dir.mkdir()
            targets = [
                codex_dir / "hooks.log",
                workspace_root / "hooks_events.csv",
                workspace_root / "hooks_tool_calls.csv",
                workspace_root / "hooks_skill_invocations.csv",
            ]
            for target in targets:
                target.write_text("data", encoding="utf-8")
            unrelated_csv = workspace_root / "unrelated.csv"
            unrelated_csv.write_text("keep me", encoding="utf-8")

            stdout = io.StringIO()
            with mock.patch(
                "clear_hooks_log.default_workspace_root", return_value=workspace_root
            ):
                with redirect_stdout(stdout):
                    exit_code = clear_hooks_log.main()

            self.assertEqual(0, exit_code)
            self.assertTrue(all(not target.exists() for target in targets))
            self.assertEqual("keep me", unrelated_csv.read_text(encoding="utf-8"))
            self.assertIn("Removed 4 files", stdout.getvalue())

    def test_main_succeeds_when_log_files_do_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)

            stdout = io.StringIO()
            with mock.patch(
                "clear_hooks_log.default_workspace_root", return_value=workspace_root
            ):
                with redirect_stdout(stdout):
                    exit_code = clear_hooks_log.main()

            self.assertEqual(0, exit_code)
            self.assertIn("Removed 0 files", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
