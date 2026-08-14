---
name: rebase-plan-mode
description: Safely rebase the current non-main feature branch onto origin/main while preserving Codex Plan mode model and reasoning-effort overrides. Use when updating a branch containing Plan mode work, resolving rebase conflicts in its configuration/UI/persistence paths, or before publishing a fork release.
---

# Rebase Plan Mode

Safely move the current feature branch onto the latest `origin/main` or an explicitly selected upstream release commit. Preserve both Plan mode choices: model and reasoning effort. In the `aaudin90/codex` fork-release workflow, perform every action on `plan-mode-model-selection`; never check out, rebase, or push `main`.

## Preconditions

1. Run `git status --short` and `git branch --show-current`.
2. Stop if the worktree is not clean, the branch is detached, or it is `main`. Do not stash changes and never rebase or force-push `main`.
3. For the `aaudin90/codex` fork-release workflow, require the branch to be exactly `plan-mode-model-selection`; do not substitute another feature branch.
4. By default, run `git fetch origin main` and use fetched `origin/main` as the rebase base. For a fork release explicitly targeting an upstream version, obtain its exact `rust-v<version>` commit without adding a permanent remote and use that commit instead.

## Rebase and resolve conflicts

1. For the default base, run `git rebase origin/main`. For an explicitly chosen release commit, run `git rebase --onto <release-commit> origin/main` so the feature-only commits move from the current main base to that release commit.
2. For every conflict, inspect the base, upstream, and branch changes before editing. Do not resolve an entire file with `git checkout --ours`, `git checkout --theirs`, or equivalent bulk replacement.
3. Keep upstream behavior and the complete Plan mode feature. In particular, verify all of these remain connected:

   - `plan_mode_model` and `plan_mode_reasoning_effort` in root/profile config, the config schema, and effective config;
   - application of both overrides on Plan mode entry, message submission, and thread-state restoration;
   - scope-popup UI, update and persist events, and persistence to the selected user config;
   - return to Default mode using the global model instead of either Plan override.

4. Use targeted edits, stage the resolved files, and continue with `git rebase --continue`. If the combined semantics cannot be established, abort with `git rebase --abort` and report the conflicting decisions.

## Verify

After a successful rebase, run from `codex-rs`:

```bash
just fmt
just test -p codex-tui
cargo insta pending-snapshots -p codex-tui
```

Read every pending `*.snap.new`. Accept only intentional Plan mode UI changes with `cargo insta accept -p codex-tui`; otherwise fix or reject them. Report formatter or test infrastructure failures separately from code failures.

## Remote updates

Do not push by default. Run `git push --force-with-lease` only when the user explicitly asks to update the remote feature branch. Invoking `$release-fork-codex` is explicit authorization to update that branch as part of preparing the release; it never authorizes a force-push of `main`.
