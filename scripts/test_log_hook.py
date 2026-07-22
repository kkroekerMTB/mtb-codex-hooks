from __future__ import annotations

import importlib.util
import json
import tempfile
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
