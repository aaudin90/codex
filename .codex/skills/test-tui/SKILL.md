---
name: test-tui
description: Guide for testing Codex TUI interactively
---

You can start and use Codex TUI to verify changes. 

Important notes:

Start interactively.
Always set RUST_LOG="trace" when starting the process.
Pass `-c log_dir=<some_temp_dir>` argument to have logs written to a specific directory to help with debugging.
When sending a test message programmatically, send text first, then send Enter in a separate write (do not send text + Enter in one burst).
Use `just codex` target to run - `just codex -c ...`

When work touches Plan mode, model configuration, thread restoration, keybindings, subagent menus, or downstream history, read the [durable fork behavior contract](../../plan-mode-model-selection.md). Preserve its text across rebases and releases; adapt implementation and checks to it. Change the contract only when the user explicitly requests a behavior change.
