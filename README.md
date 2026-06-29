# Codex Hooks Example

This repository contains a project-local Codex hooks setup that logs every
supported hook type to `hooks.log`.

## Files

- `.codex/hooks.json` configures all supported Codex hook events.
- `.codex/hooks/log_hook.py` receives each hook payload on stdin and appends a
  JSON line to `hooks.log`.
- `hooks.log` is created at the repository root when a hook runs.

Each log entry includes:

- `timestamp`
- `hook_type`
- `payload`

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
