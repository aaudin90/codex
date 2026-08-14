---
name: clean-rust-artifacts
description: Report and safely remove Rust build artifacts and caches from a project or machine. Use when disk space is consumed by Cargo target directories, Cargo registry or git caches, rustup download caches, or sccache; trigger on requests to clean Rust builds, Cargo cache, Rust artifacts, or free disk space used by Rust.
---

# Clean Rust Artifacts

Reclaim disk space without touching source code, Git history, `~/.cargo/bin`, or installed Rust toolchains by default. The bundled script only reports candidates until `--apply` is explicit.

## Inspect first

Run the report from a Rust workspace:

```bash
python3 .codex/skills/clean-rust-artifacts/scripts/clean_rust_artifacts.py --workspace codex-rs
```

Scopes:

- `project` — the exact Cargo `target_directory` reported by `cargo metadata`.
- `cargo-cache` — Cargo registry source, downloads, index, git checkouts, git database, and package cache.
- `rustup-cache` — only `downloads` and `tmp` below `RUSTUP_HOME`.
- `sccache` — standard or explicitly configured sccache directories.
- `all` — all scopes above; this is the default.

The report shows absolute paths and reclaimed-size estimates. Treat only those paths as deletion candidates; never replace them with a home-directory glob.

## Delete safely

1. Check that no `cargo`, `rustc`, or `sccache` build is active. Stop and wait if one is running.
2. Show the dry-run report to the user. Ask for confirmation unless the user explicitly asked to remove the reported scope.
3. Re-run the same command with `--apply`, for example:

```bash
python3 .codex/skills/clean-rust-artifacts/scripts/clean_rust_artifacts.py \
  --workspace codex-rs --scope all --apply
```

Cargo will redownload dependencies and rebuild affected projects afterward. Removing a project `target` directory is usually the largest safe saving.

## Toolchains are separate

Do not remove `~/.rustup/toolchains` or `~/.cargo/bin` in normal cleanup: they are installed tools, not disposable build cache. If the user explicitly wants to uninstall every Rust toolchain, first report the exact size and explain that Cargo/Rust will need reinstalling. Only then use both `--include-toolchains` and `--confirm-toolchain-removal` with `--apply`.

Never use `rm -rf` with an unresolved variable, a glob, a workspace root, or a home directory. Do not delete user-specified paths outside the script's reported candidates.
