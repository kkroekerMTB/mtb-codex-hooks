# Codex Hooks Example

This repository contains a project-local Codex hooks setup that logs every
supported hook type to `hooks.log`.

Here's the official documentation from OpenAI for codex hooks: https://developers.openai.com/codex/hooks

## Files

- `.codex/hooks.json` configures all supported Codex hook events.
- `.codex/hooks/log_hook.py` receives each hook payload on stdin and appends a
  JSON line to `hooks.log`.
- `hooks.log` is created at the repository root when a hook runs.

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

## Install

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

After that, matching hook invocations append JSONL records to `hooks.log`.

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

By default, this reads `hooks.log` and writes:

- `hooks_events.csv`: one row per hook event with flattened session, turn,
  tool, prompt, and token fields.
- `hooks_tool_calls.csv`: one row per tool call, joining `PreToolUse` and
  `PostToolUse` records by `tool_use_id` so reports can include duration and
  response previews.

You can override the paths:

```shell
python3 scripts/hooks_log_to_csv.py path/to/hooks.log \
  --events-out path/to/hooks_events.csv \
  --tool-calls-out path/to/hooks_tool_calls.csv
```
