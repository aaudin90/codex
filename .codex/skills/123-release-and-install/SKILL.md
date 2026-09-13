---
name: 123-release-and-install
description: "Run the complete Codex fork workflow after collecting release choices: update the Plan mode branch, verify behavior, publish a fresh macOS ARM64 release, clean selected Rust artifacts, and install the published CLI on this machine. Use for requests to run the full fork release and installation flow."
---

# Release and install the Codex fork

This is the entry point for the complete `aaudin90/codex` workflow. Coordinate existing skills; do not duplicate their release, checksum, extraction, or installation implementation. Creating or editing this skill does not authorize running a release.

## Collect choices before making changes

First inspect the branch, worktree, installed CLI path, and published fork tags read-only. Locate all required skills before starting. Ask only for missing choices; reuse values and authorization explicitly supplied in the user's request. Batch questions where practical and wait for answers before rebasing, publishing, deleting artifacts, or installing.

Collect:

1. Exact upstream version. If the user asks for latest, resolve the latest stable `openai/codex` release and present its exact version before proceeding; do not silently select a prerelease.
2. Fork version/tag. Suggest the upstream version if its `fork-v…` tag is unused. If occupied, offer an unused suffix such as `-fix.1`; never overwrite or move an existing release tag. Keep the upstream Cargo version unchanged.
3. Installation choice: install the new release on this machine, or publish only. For installation, suggest the directory of the current standalone fork CLI (normally `~/.local/bin`); ask about another destination only if requested or the current command resolves to a different installation type.
Full cleanup is a required default of this complete workflow: remove project Rust build artifacts, Cargo/rustup/sccache caches, and installed Rust toolchains after release verification. Announce that future builds restore the pinned toolchain. Do not ask whether to clean or silently skip cleanup; honor an explicit user request to retain a particular scope.

Summarize the selected upstream version, fork tag, installation destination/skip, and cleanup scope in one short message. Explain that the flow rewrites and pushes only `plan-mode-model-selection`. When choices and authorization are already explicit, proceed without asking again.

## Execute the selected flow

1. Read and invoke [123-release-fork-from-upstream](../123-release-fork-from-upstream/SKILL.md), passing the exact versions and cleanup choice. It coordinates [123-rebase-plan-mode](../123-rebase-plan-mode/SKILL.md), [123-release-fork-codex](../123-release-fork-codex/SKILL.md), and [123-clean-rust-artifacts](../123-clean-rust-artifacts/SKILL.md). Execute each phase once: when the inner publisher is invoked, reuse the completed final-base rebase and its verification if the candidate tree and upstream base have not changed. Do not rebase the candidate again merely because both skills describe that prerequisite.
2. Preserve exactly three downstream commits above the selected upstream release: skills/instructions, Plan mode project changes, and other downstream changes. Fold fixes into the appropriate commit before the final acceptance checks and push with `--force-with-lease`. Keep a backup ref and preserve published tags. Never check out, rebase, or push `main`.
3. Complete the [Plan mode acceptance contract](../123-rebase-plan-mode/references/plan-mode-acceptance.md) on the final candidate. Required behavioral checks, snapshots, and candidate TUI smoke checks must pass before publication. Record the candidate commit and results; a successful build or `--version` alone is insufficient.
4. Verify the published non-draft release, tag commit, canonical archive, and SHA-256 asset. Invoke the cleanup phase with `--workspace codex-rs --scope all --include-toolchains --confirm-toolchain-removal`: first report exact paths and sizes, then run the same command with `--apply` after checking that no Cargo, rustc, or sccache build is active. Invocation of this complete workflow requests this full cleanup; no second confirmation is needed. Apply any explicit user retention constraint instead of the default. Preserve `~/.cargo/bin`, installed CLI packages, source files, Git history, and the currently running session. Verify the reported directories are gone using filesystem checks; do not run Cargo afterward, which could restore the toolchain/cache. Record reclaimed size. A successful release alone does not complete this phase, and failure must be reported and resolved rather than silently skipped.
5. If installation was selected, locate and read `$install-fork-codex` from the available skill catalog (normally the personal skills directory). Invoke it with the exact newly published fork version and selected bin directory; never ask its interactive picker to choose another release. Verify the archive SHA-256, package contents, both installed executable targets, and the `codex` resolved through PATH. Since suffixed releases report the same Cargo version, verify the resolved package directory/tag as well as `codex --version`.

## Failures and network fallback

- An unavailable dependency, dirty worktree, unsynchronized `origin/main`, occupied tag, or failed Plan acceptance check stops the affected phase before publication. Report the concrete blocker and retain completed-phase evidence.
- If publication failed after pushing a tag, preserve it and report partial publication. Do not automatically rerun the fresh-only release workflow against that tag.
- If installation fails after a verified publication, retry only installation of that exact release. Do not rebase, rebuild, republish, or redo cleanup. Keep the previous installed package usable until its replacement is verified.
- Distinguish `github.com` and `api.github.com` from the redirected `release-assets.githubusercontent.com` download host. Direct requests can time out only on the asset host. Use bounded connection/total timeouts for diagnostics. If direct downloading fails, download the exact release archive and checksum using `gh release download --repo aaudin90/codex` and reuse the install skill's checksum, safe extraction, package validation, and atomic symlink functions. Do not disable TLS verification, bypass checksums, change global proxy settings, or fetch upstream/package-manager binaries. Stop any superseded installer and confirm it exited before starting the fallback installation.

## Completion

Report the release URL/tag, final three-commit branch state, Plan acceptance result, cleanup result, and installed package path (or installation explicitly skipped). If installed, explain that existing sessions must restart to use the new binary. Do not claim full completion while a selected phase remains unverified.
