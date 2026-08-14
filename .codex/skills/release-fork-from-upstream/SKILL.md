---
name: release-fork-from-upstream
description: Create a fresh Codex fork release from the exact commit of an openai/codex version, then reclaim Rust build and cache space. Use when asked to rebase a fork branch onto a specific upstream Codex release, publish fork-vX.Y.Z from scratch, and clean Rust artifacts after the verified release.
---

# Release Fork From Upstream

Orchestrate `$rebase-plan-mode`, `$release-fork-codex`, and `$clean-rust-artifacts` in that order. Accept an upstream version matching `X.Y.Z[-alpha…|-beta…]` and an optional fork version `X.Y.Z[-prerelease]`; a run is fresh-only and never resumes a partially published release. The fork version names the downstream `fork-v…` tag and Release without changing the upstream Cargo version. Run every Git action on `plan-mode-model-selection`; never check out, rebase, or push `main`.

## 1. Preflight and exact release base

1. Require a clean worktree, `git branch --show-current` equal to `plan-mode-model-selection`, `gh` authentication with release permission, and a matching `codex-rs/Cargo.toml` version after the rebase. Stop on any other branch; do not repair this by switching to or updating `main`.
2. Refuse to start if local or remote `fork-v<fork-version>` already exists, or GitHub already has that release. Do not delete, retag, overwrite, or resume it. Default `<fork-version>` to `<upstream-version>`.
3. Resolve the immutable upstream commit with the bundled read-only script:

```bash
python3 .codex/skills/release-fork-from-upstream/scripts/resolve_upstream_release.py <version>
```

4. Fetch its `rust-v<version>` tag transiently from `https://github.com/openai/codex.git` with `NO_PROXY="*"`; do not add a permanent `upstream` remote. Confirm the printed commit exists locally.

## 2. Synchronize the base, then rebase and verify Plan mode

First verify that the fork's remote `main` is already synchronized with the current `openai/codex` `main`; do not mutate either `main` branch. Fetch upstream transiently and record the printed SHA before fetching origin:

```bash
NO_PROXY="*" git fetch --no-tags https://github.com/openai/codex.git main
git rev-parse FETCH_HEAD
git fetch origin main
git rev-parse origin/main
```

If the two printed SHAs differ, stop and request that `origin/main` be synchronized with upstream. Do not continue with a stale `origin/main` and do not push or rebase `main` yourself.

Invoke `$rebase-plan-mode` on `plan-mode-model-selection` in two steps. First integrate the updated fork main, then move only the feature commits to the immutable release base:

```bash
git fetch origin main
git rebase origin/main
git rebase --onto <upstream-release-commit> origin/main
```

Resolve every conflict semantically, retaining both model and reasoning-effort Plan mode overrides. Do not use whole-file `--ours` or `--theirs`. Then run its required `just fmt`, `just test -p codex-tui`, and pending-Insta review. Treat unavailable `uv`/`dotslash` as formatter infrastructure failures, not passing formatting.

Before those Rust checks, install the channel and components pinned in `codex-rs/rust-toolchain.toml` if cleanup removed them:

```bash
NO_PROXY="*" rustup toolchain install <channel-from-rust-toolchain.toml> --profile minimal --no-self-update
NO_PROXY="*" rustup component add <components-from-rust-toolchain.toml> --toolchain <channel-from-rust-toolchain.toml>
```

After verification, update only `plan-mode-model-selection` with `git push --force-with-lease`; this meta-skill is explicit authorization for that push and never for `main`.

## 3. Publish a new fork release

Invoke `$release-fork-codex` for the upstream version and optional fork version, first with `--dry-run`, then `--publish`. For example, use upstream `0.147.0` with fork version `0.147.0-test` to create `fork-v0.147.0-test`. It must verify the exact upstream commit is an ancestor, build the canonical macOS ARM64 package, create the annotated fork tag at current `HEAD`, upload the package archive and SHA-256, and create the GitHub Release in `aaudin90/codex`.

If publishing fails at any point after pushing the tag, stop and report the tag and failure. A later invocation is not a continuation: it must refuse because the tag already exists.

## 4. Verify release, then clean Rust artifacts

Verify that the GitHub Release is non-draft, has the expected tag, and contains `codex-package-aarch64-apple-darwin.tar.gz` plus its SHA-256 asset. Do not clean before this succeeds.

Then invoke `$clean-rust-artifacts` from the repository root:

```bash
python3 .codex/skills/clean-rust-artifacts/scripts/clean_rust_artifacts.py --workspace codex-rs --scope all
python3 .codex/skills/clean-rust-artifacts/scripts/clean_rust_artifacts.py --workspace codex-rs --scope all --apply
```

This meta-skill's explicit cleanup request authorizes the second command after the dry-run report. If the user has explicitly opted into removing installed toolchains, add `--include-toolchains --confirm-toolchain-removal` to the report and apply commands; the next release restores the pinned channel automatically. Wait for all Cargo/Rust processes first. Never remove `~/.cargo/bin`.

## Completion report

Report upstream tag and commit, fork tag and commit, release URL and asset names, rebase/test/formatter status, and reclaimed Rust-cache size. On any stop condition, state which stage failed and whether a remote tag or Release was created.
