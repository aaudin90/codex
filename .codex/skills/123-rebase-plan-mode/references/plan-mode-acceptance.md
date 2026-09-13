# Plan mode acceptance contract

Read before resolving Plan mode conflicts and before publishing a fork. This contract defines downstream behavior independently of upstream tests.

## Required behavior

- In Plan mode, selecting a different ordinary model must open the scope prompt, even when reasoning effort is unchanged. Selecting the current model with a changed effort must also open it. A true no-op may skip it only if both effective Plan values and global defaults are unchanged.
- Selecting Plan-only updates and persists the Plan model and effort, leaves global defaults unchanged, and keeps Plan active. The next submission uses Plan mode and the selected override.
- Selecting all modes updates both global and Plan values and keeps Plan active.
- Leaving Plan restores the global model and effort; entering Plan again restores its overrides. Restart/resume must preserve the saved overrides, including profile configuration.
- Luna Reserve retains its temporary, non-persisting behavior and bypasses the ordinary scope prompt.

## Regression checks

Cover the different-model selection through the actual model/reasoning popup event path, not only by directly opening the scope popup. Assert that it emits `OpenPlanReasoningScopePrompt` and no global update/persist events before scope selection. Exercise Plan-only through override application and the next submission; assert that Plan remains active and global defaults are unchanged. Keep snapshot coverage for the scope popup.

The 0.154.0 regression came from an early return on `selected_model != current_model()` in the scope decision. Do not reintroduce that semantic restriction through a renamed helper or another popup path. Review pre-/post-rebase test diffs; upstream expectations do not override this contract.

## Candidate TUI smoke check before publication

Use `$test-tui` with the candidate built from the commit to be published and an isolated config. Record commit, binary path, actions, and observed results. Enter Plan, select another ordinary model with the same effort, choose Plan-only, and verify that Plan remains active. Switch to Default and back and verify each model/effort pair. Restart with that isolated config and verify persistence. Exercise the all-modes choice as well. Do not use the previously installed release as evidence for the candidate.

If the candidate cannot be exercised, report the missing check and stop before publishing. A checksum, `--version`, a successful build, or snapshots alone do not establish these behaviors. Any later code change or rebase invalidates the affected checks.
