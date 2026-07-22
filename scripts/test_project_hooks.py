from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_CONFIG_PATH = REPO_ROOT / ".codex" / "hooks.json"
LOG_HOOK_PATH = REPO_ROOT / ".codex" / "hooks" / "log_hook.py"
CSV_EXPORT_PATH = REPO_ROOT / "scripts" / "hooks_log_to_csv.py"


class ProjectHooksTest(unittest.TestCase):
    @staticmethod
    def command_for_current_platform(command_hook: dict) -> str:
        if os.name == "nt":
            return command_hook["commandWindows"]
        return command_hook["command"]

    def test_every_hook_has_a_valid_windows_override(self) -> None:
        config = json.loads(HOOKS_CONFIG_PATH.read_text(encoding="utf-8"))

        for event_name, entries in config["hooks"].items():
            for entry in entries:
                for command_hook in entry["hooks"]:
                    with self.subTest(event=event_name, status=command_hook["statusMessage"]):
                        windows_command = command_hook["commandWindows"]
                        self.assertTrue(windows_command.startswith('py -3 -c "'))
                        self.assertNotIn("Path.home", windows_command)
                        code = windows_command.split(' -c "', 1)[1].removesuffix('"')
                        compile(code, "<generated Windows hook command>", "exec")

    def test_logger_runs_from_a_workspace_subdirectory(self) -> None:
        config = json.loads(HOOKS_CONFIG_PATH.read_text(encoding="utf-8"))
        command_hook = config["hooks"]["SessionStart"][0]["hooks"][0]

        self.assertIn("commandWindows", command_hook)
        self.assertNotIn("Path.home", command_hook["command"])
        self.assertNotIn("Path.home", command_hook["commandWindows"])

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            hooks_dir = workspace_root / ".codex" / "hooks"
            nested_dir = workspace_root / "src" / "nested"
            hooks_dir.mkdir(parents=True)
            nested_dir.mkdir(parents=True)
            shutil.copy2(LOG_HOOK_PATH, hooks_dir / "log_hook.py")
            subprocess.run(
                ["git", "init", "--quiet"],
                cwd=workspace_root,
                check=True,
            )

            result = subprocess.run(
                self.command_for_current_platform(command_hook),
                cwd=nested_dir,
                input='{"session_id": "session-1"}',
                text=True,
                shell=True,
                capture_output=True,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((workspace_root / "hooks.log").is_file())

    def test_csv_export_runs_from_a_workspace_subdirectory(self) -> None:
        config = json.loads(HOOKS_CONFIG_PATH.read_text(encoding="utf-8"))
        command_hook = config["hooks"]["Stop"][0]["hooks"][1]

        self.assertIn("commandWindows", command_hook)
        self.assertNotIn("Path.home", command_hook["command"])
        self.assertNotIn("Path.home", command_hook["commandWindows"])

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            scripts_dir = workspace_root / "scripts"
            nested_dir = workspace_root / "src" / "nested"
            scripts_dir.mkdir(parents=True)
            nested_dir.mkdir(parents=True)
            shutil.copy2(CSV_EXPORT_PATH, scripts_dir / "hooks_log_to_csv.py")
            (workspace_root / "hooks.log").write_text(
                '{"hook_type": "Stop", "payload": {}}\n',
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "init", "--quiet"],
                cwd=workspace_root,
                check=True,
            )

            result = subprocess.run(
                self.command_for_current_platform(command_hook),
                cwd=nested_dir,
                text=True,
                shell=True,
                capture_output=True,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((workspace_root / "hooks_events.csv").is_file())


if __name__ == "__main__":
    unittest.main()
