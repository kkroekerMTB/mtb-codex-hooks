from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


LOG_HOOK_PATH = Path(__file__).resolve().parents[1] / ".codex" / "hooks" / "log_hook.py"
SPEC = importlib.util.spec_from_file_location("log_hook", LOG_HOOK_PATH)
log_hook = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(log_hook)


class LogHookTest(unittest.TestCase):
    def test_log_path_uses_codex_directory_containing_hook_script(self) -> None:
        self.assertEqual(
            LOG_HOOK_PATH.parent.parent / "hooks.log",
            log_hook.log_path(),
        )


if __name__ == "__main__":
    unittest.main()
