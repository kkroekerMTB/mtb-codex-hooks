from __future__ import annotations

import importlib.util
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
    def test_log_path_ignores_codex_hooks_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            ignored_path = home / "elsewhere" / "hooks.log"

            with mock.patch.dict(
                "os.environ",
                {"CODEX_HOOKS_LOG_PATH": str(ignored_path)},
            ):
                with mock.patch("pathlib.Path.home", return_value=home):
                    self.assertEqual(home / ".codex" / "hooks.log", log_hook.log_path())


if __name__ == "__main__":
    unittest.main()
