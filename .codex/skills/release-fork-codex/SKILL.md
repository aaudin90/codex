---
name: release-fork-codex
description: Publish a macOS ARM64 release of the current Codex fork HEAD after validating it against an exact openai/codex release. Use when asked to create a fork release, publish fork-vX.Y.Z, or package the current branch against an upstream Codex version.
---

# Release Codex Fork

Publish the current `plan-mode-model-selection` `HEAD` to `aaudin90/codex` as `fork-v<fork-version>`. The release includes downstream changes, including Plan mode, and is not the upstream release commit. Never check out, rebase, or push `main`.

## Inputs and safety

Accept an upstream version matching `X.Y.Z[-alpha…|-beta…]`; normalize it to `rust-v<version>`. An optional `--fork-version X.Y.Z[-prerelease]` names only the downstream tag and Release; it defaults to the upstream version. For example, upstream `0.147.0` with `--fork-version 0.147.0-test` uses `rust-v0.147.0`, keeps Cargo at `0.147.0`, and publishes `fork-v0.147.0-test`. Require `git branch --show-current` to print exactly `plan-mode-model-selection`. Never create a version-bump commit.

Start with the script's safe default:

```bash
python3 .codex/skills/release-fork-codex/scripts/publish_fork_release.py <upstream-version> --fork-version <fork-version> --dry-run
```

Use `--publish` only after the dry-run succeeds:

```bash
python3 .codex/skills/release-fork-codex/scripts/publish_fork_release.py <upstream-version> --fork-version <fork-version> --publish
```

The script uses only the Python standard library plus `git`, `gh`, `cargo`, `rustup`, and `shasum`. It prefixes every networked subprocess with `NO_PROXY="*"` through its environment.

## Workflow

1. First invoke `$rebase-plan-mode` on `plan-mode-model-selection` after confirming `origin/main` has been synchronized with `openai/codex` main. Then move its feature-only commits to the exact upstream release commit. A fork release explicitly authorizes its guarded `git push --force-with-lease` for `plan-mode-model-selection` after a successful rebase.
2. Run the release script in dry-run mode. It resolves the exact upstream tag commit through the GitHub API, obtains it transiently from the Git URL if necessary without adding an `upstream` remote, and requires that exact commit to be an ancestor of `HEAD`.
3. Stop before publishing if the worktree is dirty, version or ancestry is wrong, GitHub authentication lacks push permission to `aaudin90/codex`, or the fork tag/release already exists. Do not bypass these checks.
4. Run with `--publish`. If absent, it installs the channel and components from `codex-rs/rust-toolchain.toml` through `rustup`, then builds `codex-cli` with that pinned channel for the current macOS ARM64 host. It restores a build-generated `Cargo.lock` change after the clean precheck, verifies the upstream Cargo version in `codex --version`, creates an annotated `fork-v<fork-version>` tag at current `HEAD`, pushes that tag, then creates the GitHub release with the aarch64 macOS binary and SHA-256 file.
5. Check the generated notes: upstream tag and exact commit, fork commit, and a bounded downstream log are required.

Do not use the standard `rust-release` workflow: it targets `rust-v…`, requires upstream Cargo-version matching and release secrets, and produces a multi-platform upstream release. If publishing fails after the tag push, leave the tag in place and report the failure; do not delete it automatically.
