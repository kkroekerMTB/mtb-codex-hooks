# Codex Hooks Example

This repository contains a Codex hooks setup that logs every supported hook type
to a shared JSONL log at `~/.codex/hooks.log`.

Here's the official documentation from OpenAI for codex hooks: https://developers.openai.com/codex/hooks

## Files

- `.codex/hooks.json` configures all supported Codex hook events.
- `.codex/hooks/log_hook.py` receives each hook payload on stdin and appends a
  JSON line to the shared log.
- `scripts/hooks_log_to_csv.py` converts the shared JSONL log into CSV reports.
- `~/.codex/hooks.log` is created when a hook runs.

Set `CODEX_HOOKS_LOG_PATH` before starting Codex to write to a different shared
log file.

Each log entry includes:

- `timestamp`
- `hook_type`
- `payload`
- `token_usage`

`token_usage` is a best-effort snapshot read from the hook payload's
`transcript_path`. It includes the latest known cumulative token usage and the
latest completed model-call usage at the time the hook runs. Early hooks may
show `null` values before Codex has written a token-count event to the
transcript.

## Install In One Repository

1. Copy or keep the `.codex/` directory at the root of the repository where you
   want these hooks to run.

2. Start Codex from inside that repository.

3. Make sure the project is trusted. Project-local hooks are loaded only when
   the project `.codex/` layer is trusted.

4. In the Codex CLI, run:

   ```text
   /hooks
   ```

5. Review and trust the hook definitions. Codex records trust for the exact hook
   configuration, so changing `.codex/hooks.json` or the command definitions may
   require reviewing them again.

After that, matching hook invocations append JSONL records to
`~/.codex/hooks.log`.

## Install For Every Codex Repository

Codex also loads user-level hooks from `~/.codex/hooks.json`. Use this when you
want the logger to run from any repository where you start Codex, without
copying this repository's `.codex/` directory into each project.

To build the user-level artifacts from the current hook setup in this
repository, run:

```shell
python3 scripts/publish.py
```

This recreates `dist/codex-logging-hooks/` with exactly the files that belong in
a user's `~/.codex` directory:

- `hooks.json`
- `hooks/log_hook.py`
- `hooks/hooks_log_to_csv.py`

Then install them with:

```shell
python3 scripts/install.py
```

The install script runs `scripts/publish.py` with the default output directory,
then copies the published artifacts into `~/.codex`, overwriting the installed
`hooks.json` and published files under `~/.codex/hooks/`.

To install into another Codex directory, run:

```shell
python3 scripts/install.py --codex-dir /path/to/.codex
```

The publish script rewrites the hook commands from repository-local paths to
user-level paths under `$HOME/.codex/hooks/`.

Manual installation does the same thing explicitly:

1. Put the hook scripts somewhere stable in your user Codex directory:

   ```shell
   mkdir -p ~/.codex/hooks
   cp .codex/hooks/log_hook.py ~/.codex/hooks/log_hook.py
   cp scripts/hooks_log_to_csv.py ~/.codex/hooks/hooks_log_to_csv.py
   chmod +x ~/.codex/hooks/log_hook.py
   chmod +x ~/.codex/hooks/hooks_log_to_csv.py
   ```

2. Copy this repository's hook configuration to your user-level Codex config:

   ```shell
   cp .codex/hooks.json ~/.codex/hooks.json
   ```

3. Edit `~/.codex/hooks.json` and replace every command that points at the
   repository-local script:

   ```json
   "python3 \"$(git rev-parse --show-toplevel)/.codex/hooks/log_hook.py\" SessionStart"
   ```

   with the user-level script path:

   ```json
   "python3 \"$HOME/.codex/hooks/log_hook.py\" SessionStart"
   ```

   Keep the hook type argument at the end of each logger command, changing only
   the script path. For example, the `PreToolUse` command should end with
   `PreToolUse`, the `PostToolUse` command should end with `PostToolUse`, and
   so on.

   Also replace the project-local `Stop` CSV export command:

   ```json
   "cd \"$(git rev-parse --show-toplevel)\" && python3 \"$HOME/.codex/hooks/hooks_log_to_csv.py\""
   ```

   This forces the globally installed hook to run from the workspace root, so
   the CSV files are still written next to that repository.

4. Start Codex from any repository and run:

   ```text
   /hooks
   ```

5. Review and trust the user-level hook definitions.

After that, matching hook invocations from every workspace append JSONL records
to the same `~/.codex/hooks.log` file.

Codex loads matching hooks from all active hook sources, so avoid installing the
same logger both user-level and project-local unless you intentionally want
duplicate log entries.

For one-off automation that already vets the hook source outside Codex, you can
launch Codex with:

```shell
codex --dangerously-bypass-hook-trust
```

Use that flag only when you intentionally want to skip persisted hook trust for
that run.

## Supported Hook Types

This example configures:

- `SessionStart`
- `PreToolUse`
- `PermissionRequest`
- `PostToolUse`
- `PreCompact`
- `PostCompact`
- `UserPromptSubmit`
- `SubagentStart`
- `SubagentStop`
- `Stop`

## Power BI CSV Export

Convert the append-only JSONL log into CSV files with:

```shell
python3 scripts/hooks_log_to_csv.py
```

By default, this reads `~/.codex/hooks.log` and writes:

- `hooks_events.csv`: one row per hook event with flattened session, turn,
  tool, prompt, and token fields.
- `hooks_tool_calls.csv`: one row per tool call, joining `PreToolUse` and
  `PostToolUse` records by `tool_use_id` so reports can include duration and
  response previews.

The `Stop` hook runs this command from the repository root after logging the
stop event, so the CSV reports are refreshed at the end of each conversation.
The script resolves the current workspace root with `git rev-parse
--show-toplevel` when available and writes the CSV reports there.

You can override the paths:

```shell
python3 scripts/hooks_log_to_csv.py path/to/hooks.log \
  --events-out path/to/hooks_events.csv \
  --tool-calls-out path/to/hooks_tool_calls.csv
```
