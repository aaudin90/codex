# Fork behavior acceptance contract

Read before resolving downstream conflicts and before publishing a fork. The durable source of behavior is [plan-mode-model-selection.md](../../../plan-mode-model-selection.md); read and preserve it unchanged. This file describes implementation-specific acceptance checks and may evolve without changing that contract.

## Required behavior

- In Plan mode, selecting a different ordinary model must open the scope prompt, even when reasoning effort is unchanged. Selecting the current model with a changed effort must also open it. A true no-op may skip it only if both effective Plan values and global defaults are unchanged.
- Selecting Plan-only updates and persists the Plan model and effort, leaves global defaults unchanged, and keeps Plan active. The next submission uses Plan mode and the selected override.
- Selecting all modes updates both global and Plan values and keeps Plan active.
- Leaving Plan restores the global model and effort; entering Plan again restores its overrides. Restart/resume must preserve the saved overrides, including profile configuration.
- Luna Reserve retains its temporary, non-persisting behavior and bypasses the ordinary scope prompt.

## Regression checks

Cover the different-model selection through the actual model/reasoning popup event path, not only by directly opening the scope popup. Assert that it emits `OpenPlanReasoningScopePrompt` and no global update/persist events before scope selection. Exercise Plan-only through override application and the next submission; assert that Plan remains active and global defaults are unchanged. Keep snapshot coverage for the scope popup.

The 0.154.0 regression came from an early return on `selected_model != current_model()` in the scope decision. Do not reintroduce that semantic restriction through a renamed helper or another popup path. Review pre-/post-rebase test diffs; upstream expectations do not override this contract.

## Focused checks on the final candidate

Run from `codex-rs` through the repository test runner:

```bash
just test -p codex-tui -E 'test(plan_mode) | test(luna_reserve) | test(replay_thread_snapshot_restores_collaboration_mode) | test(configured_open_agents) | test(key_chords) | test(keymap_setup) | test(unavailable_commands) | test(agents_navigation)'
```

The replay checks matter even though their names omit `plan_mode`. Model and effort overrides must survive input-state capture, replacement, replay, and subsequent Default/Plan switching. Use the same persisted Plan model in original and replacement widget config; construct overrides through their setters. A manually injected mask is not a persisted Plan model override.

## Candidate TUI smoke check before publication

Use `$test-tui` with the candidate built from the commit to be published and an isolated config. Record commit, binary path, actions, and observed results. Enter Plan, select another ordinary model with the same effort, choose Plan-only, and verify that Plan remains active. Switch to Default and back and verify each model/effort pair. Restart with that isolated config and verify persistence. Exercise the all-modes choice as well. Do not use the previously installed release as evidence for the candidate.

If the candidate cannot be exercised, report the missing check and stop before publishing. A checksum, `--version`, a successful build, or snapshots alone do not establish these behaviors. Any later code change or rebase invalidates the affected checks.

## Subagent shortcut acceptance

The durable contract also covers `tui.keymap.global.open_agents`: it opens the same current-thread picker as `/subagents`, for single keys and key sequences. Preserve the existing config name, feature gating, modal routing, and composer draft. `/agents` and other overview entry points retain the shared agent-session overview.

Review every path that resolves `open_agents`, including app-level single keys and global chord dispatch. Exercise each through input handling; comparing static config values or calling the picker directly is insufficient. Keep snapshot coverage for changed shortcut descriptions or rendered menus. Run focused navigation/keymap tests and `just test -p codex-tui` when this broader input behavior changes.

During candidate TUI smoke, configure `open_agents` in isolated config. With a draft present, press the configured shortcut, verify the current-thread subagent picker, and cancel it to verify the draft. Repeat with a configured key sequence. Compare `/subagents` and verify `/agents` still opens the overview. Check disabled Subagents behavior through the same feature prompt as `/subagents`. Record the tested commit and results together with Plan mode acceptance. Missing or failed shortcut checks block publication.
