from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish


class PublishTest(unittest.TestCase):
    def test_user_level_log_command_uses_python_home_resolution(self) -> None:
        command = publish.user_level_log_command(
            "SessionStart",
            'python .codex/hooks/log_hook.py SessionStart',
        )

        self.assertTrue(command.startswith(f'"{sys.executable}" -c '))
        self.assertIn("Path.home()/'.codex'/'hooks'/'log_hook.py", command)
        self.assertIn("'SessionStart'", command)
        self.assertNotIn("$HOME", command)
        self.assert_generated_python_is_valid(command)

    def test_user_level_csv_export_command_uses_python_home_resolution(self) -> None:
        command = publish.user_level_csv_export_command("Stop")

        self.assertTrue(command.startswith('cd "$(git rev-parse --show-toplevel)" && '))
        self.assertIn(f'"{sys.executable}" -c ', command)
        self.assertIn("Path.home()/'.codex'/'hooks'/'hooks_log_to_csv.py", command)
        self.assertNotIn("$HOME", command)
        self.assert_generated_python_is_valid(command)

    def test_user_level_command_accepts_windows_style_project_paths(self) -> None:
        command = publish.user_level_command(
            "PreToolUse",
            r"python .codex\hooks\log_hook.py PreToolUse",
        )

        self.assertIn("'PreToolUse'", command)

    def assert_generated_python_is_valid(self, command: str) -> None:
        if command.startswith('cd "$(git rev-parse --show-toplevel)" && '):
            command = command.removeprefix('cd "$(git rev-parse --show-toplevel)" && ')
        code = command.split(' -c "', 1)[1].removesuffix('"')
        compile(code, "<generated hook command>", "exec")


if __name__ == "__main__":
    unittest.main()
