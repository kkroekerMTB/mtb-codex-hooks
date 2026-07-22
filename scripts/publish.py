#!/usr/bin/env python3
"""Build the user-level Codex hook artifacts for publishing."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_HOOKS_JSON = REPO_ROOT / ".codex" / "hooks.json"
PROJECT_LOG_HOOK = REPO_ROOT / ".codex" / "hooks" / "log_hook.py"
PROJECT_CSV_EXPORT = REPO_ROOT / "scripts" / "hooks_log_to_csv.py"
PROJECT_REPORT_GENERATOR = (
    REPO_ROOT / "report" / "bin" / "generate_hooks_report.mjs"
)
DEFAULT_OUTPUT = REPO_ROOT / "dist" / "codex-logging-hooks"
PYTHON_EXECUTABLE = Path(sys.executable)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create the exact files that should be copied into a user's "
            ".codex directory to install the logging hooks globally."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "Directory to write. Defaults to dist/codex-logging-hooks. "
            "The directory is recreated on each run."
        ),
    )
    args = parser.parse_args()

    output_dir = publish(args.output)

    print(f"Published Codex hook artifacts to {output_dir}")
    print("Copy the contents of that directory into ~/.codex")
    return 0


def publish(output: Path = DEFAULT_OUTPUT) -> Path:
    output_dir = output.resolve()
    assert_safe_output_dir(output_dir)

    hooks_config = read_json(PROJECT_HOOKS_JSON)
    published_config = publishable_hooks_config(hooks_config)

    recreate_dir(output_dir)
    hooks_dir = output_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    write_json(output_dir / "hooks.json", published_config)
    shutil.copy2(PROJECT_LOG_HOOK, hooks_dir / "log_hook.py")
    make_executable(hooks_dir / "log_hook.py")
    shutil.copy2(PROJECT_CSV_EXPORT, hooks_dir / "hooks_log_to_csv.py")
    make_executable(hooks_dir / "hooks_log_to_csv.py")
    shutil.copy2(PROJECT_REPORT_GENERATOR, hooks_dir / "generate_hooks_report.mjs")
    make_executable(hooks_dir / "generate_hooks_report.mjs")

    return output_dir


def assert_safe_output_dir(output_dir: Path) -> None:
    project_codex_dir = REPO_ROOT / ".codex"
    if output_dir == REPO_ROOT:
        raise SystemExit("Refusing to publish over the repository root.")
    if output_dir == project_codex_dir or project_codex_dir in output_dir.parents:
        raise SystemExit("Refusing to publish over this repository's .codex directory.")


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def write_json(path: Path, value: dict) -> None:
    with path.open("w", encoding="utf-8") as json_file:
        json.dump(value, json_file, indent=2)
        json_file.write("\n")


def recreate_dir(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise SystemExit(f"Output path exists and is not a directory: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)


def make_executable(path: Path) -> None:
    if os.name == "nt":
        return

    path.chmod(0o755)


def publishable_hooks_config(config: dict) -> dict:
    published = json.loads(json.dumps(config))
    hooks_by_event = published.get("hooks")
    if not isinstance(hooks_by_event, dict):
        raise SystemExit("Expected .codex/hooks.json to contain a hooks object.")

    for event_name, hook_entries in hooks_by_event.items():
        if not isinstance(hook_entries, list):
            raise SystemExit(f"Expected hooks.{event_name} to be a list.")

        for entry in hook_entries:
            commands = entry.get("hooks") if isinstance(entry, dict) else None
            if not isinstance(commands, list):
                raise SystemExit(f"Expected hooks.{event_name} entries to contain hooks lists.")

            for hook in commands:
                if not isinstance(hook, dict):
                    raise SystemExit(f"Expected hooks.{event_name} command entries to be objects.")

                hook["command"] = user_level_command(event_name, hook.get("command"))
                hook.pop("commandWindows", None)

    return published


def user_level_command(event_name: str, command: object) -> str:
    if not isinstance(command, str):
        raise SystemExit(f"Expected {event_name} hook command to be a string.")

    normalized_command = command.replace("\\", "/")

    if ".codex/hooks/log_hook.py" in normalized_command:
        return user_level_log_command(event_name, command)

    if "scripts/hooks_log_to_csv.py" in normalized_command:
        return user_level_csv_export_command(event_name)

    raise SystemExit(f"Unexpected {event_name} hook command: {command!r}")


def user_level_log_command(event_name: str, command: str) -> str:
    hook_type = command.rsplit(" ", 1)[-1].strip()
    if hook_type != event_name:
        raise SystemExit(
            f"Expected {event_name} command to end with its hook type; got {command!r}."
        )

    return user_level_python_command(
        "Path.home()/'.codex'/'hooks'/'log_hook.py'",
        [repr(hook_type)],
    )


def user_level_csv_export_command(event_name: str) -> str:
    if event_name != "Stop":
        raise SystemExit(f"CSV export is only expected on Stop hooks, got {event_name}.")

    return user_level_python_command(
        "Path.home()/'.codex'/'hooks'/'hooks_log_to_csv.py'",
        ["str(Path.home()/'.codex'/'hooks.log')"],
    )


def user_level_python_command(script_expression: str, arguments: list[str]) -> str:
    argv = ", ".join(["str(script)", *arguments])
    code = (
        "from pathlib import Path; import runpy, sys; "
        f"script={script_expression}; "
        f"sys.argv=[{argv}]; "
        "runpy.run_path(str(script), run_name='__main__')"
    )
    return f'{quote_command_argument(str(PYTHON_EXECUTABLE))} -c "{code}"'


def quote_command_argument(value: str) -> str:
    return f'"{value.replace(chr(34), chr(92) + chr(34))}"'


if __name__ == "__main__":
    raise SystemExit(main())
