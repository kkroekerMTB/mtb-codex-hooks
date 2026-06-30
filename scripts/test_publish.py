from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish


class PublishTest(unittest.TestCase):
    def test_user_level_log_command_directly_executes_installed_script(self) -> None:
        command = publish.user_level_log_command(
            "SessionStart",
            'python .codex/hooks/log_hook.py SessionStart',
        )

        self.assertIn('"python3" "$HOME/.codex/hooks/log_hook.py" "SessionStart"', command)
        self.assertIn('"python" "$HOME/.codex/hooks/log_hook.py" "SessionStart"', command)
        self.assertIn(
            r'"python3" "%USERPROFILE%\.codex\hooks\log_hook.py" "SessionStart"',
            command,
        )
        self.assertNotIn(" -c ", command)
        self.assertNotIn("runpy", command)

    def test_user_level_csv_export_command_directly_executes_installed_script(self) -> None:
        command = publish.user_level_csv_export_command("Stop")

        self.assertIn('"python3" "$HOME/.codex/hooks/hooks_log_to_csv.py"', command)
        self.assertIn('"--events-out" "$HOME/.codex/hooks_events.csv"', command)
        self.assertIn('"--tool-calls-out" "$HOME/.codex/hooks_tool_calls.csv"', command)
        self.assertIn(
            r'"python3" "%USERPROFILE%\.codex\hooks\hooks_log_to_csv.py"',
            command,
        )
        self.assertIn(
            r'"--events-out" "%USERPROFILE%\.codex\hooks_events.csv"',
            command,
        )
        self.assertIn(
            r'"--tool-calls-out" "%USERPROFILE%\.codex\hooks_tool_calls.csv"',
            command,
        )
        self.assertNotIn(" -c ", command)
        self.assertNotIn("runpy", command)

    def test_user_level_command_accepts_windows_style_project_paths(self) -> None:
        command = publish.user_level_command(
            "PreToolUse",
            r"python .codex\hooks\log_hook.py PreToolUse",
        )

        self.assertIn('"PreToolUse"', command)


if __name__ == "__main__":
    unittest.main()
