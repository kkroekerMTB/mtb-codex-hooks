from __future__ import annotations

import sys
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish


class PublishTest(unittest.TestCase):
    def test_publish_includes_standalone_report_generator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = publish.publish(Path(temporary_directory) / "published")
            generator = output / "hooks" / "generate_hooks_report.mjs"

            self.assertEqual(
                generator.read_bytes(),
                publish.PROJECT_REPORT_GENERATOR.read_bytes(),
            )
            if sys.platform != "win32":
                self.assertTrue(generator.stat().st_mode & 0o111)

    def test_publish_does_not_keep_project_windows_overrides(self) -> None:
        project_config = publish.read_json(publish.PROJECT_HOOKS_JSON)

        published_config = publish.publishable_hooks_config(project_config)

        for entries in published_config["hooks"].values():
            for entry in entries:
                for command_hook in entry["hooks"]:
                    self.assertNotIn("commandWindows", command_hook)

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

    def test_user_level_csv_export_command_uses_script_default_log(self) -> None:
        command = publish.user_level_csv_export_command("Stop")

        self.assertTrue(command.startswith(f'"{sys.executable}" -c '))
        self.assertIn("Path.home()/'.codex'/'hooks'/'hooks_log_to_csv.py", command)
        self.assertNotIn("hooks.log", command)
        self.assertNotIn("$HOME", command)
        self.assertNotIn("git rev-parse", command)
        self.assertNotIn("&&", command)
        self.assert_generated_python_is_valid(command)

    def test_published_logger_uses_platform_log_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            published = publish.publish(temporary_root / ".codex")
            config = publish.read_json(published / "hooks.json")
            command = config["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            workspace_root = temporary_root / "workspace"
            nested_dir = workspace_root / "src" / "nested"
            nested_dir.mkdir(parents=True)
            subprocess.run(["git", "init", "--quiet"], cwd=workspace_root, check=True)
            environment = os.environ.copy()
            environment["HOME"] = str(temporary_root)
            environment["USERPROFILE"] = str(temporary_root)

            result = subprocess.run(
                command,
                cwd=nested_dir,
                input='{"session_id": "session-1"}',
                text=True,
                shell=True,
                capture_output=True,
                env=environment,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            expected_log = (
                temporary_root / ".codex" / "hooks.log"
                if sys.platform == "win32"
                else workspace_root / "hooks.log"
            )
            self.assertTrue(expected_log.is_file())

    def test_user_level_command_accepts_windows_style_project_paths(self) -> None:
        command = publish.user_level_command(
            "PreToolUse",
            r"python .codex\hooks\log_hook.py PreToolUse",
        )

        self.assertIn("'PreToolUse'", command)

    def assert_generated_python_is_valid(self, command: str) -> None:
        code = command.split(' -c "', 1)[1].removesuffix('"')
        compile(code, "<generated hook command>", "exec")


if __name__ == "__main__":
    unittest.main()
