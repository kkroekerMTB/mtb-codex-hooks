from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hooks_log_to_csv


class HooksLogToCsvTest(unittest.TestCase):
    def test_main_keeps_stdout_empty_for_stop_hook_json_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            log_path = temp_path / "hooks.log"
            events_path = temp_path / "hooks_events.csv"
            tool_calls_path = temp_path / "hooks_tool_calls.csv"
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
                sys.argv = [
                    "hooks_log_to_csv.py",
                    str(log_path),
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
