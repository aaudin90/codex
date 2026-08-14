#!/usr/bin/env python3
"""Validate and optionally publish a single-platform Codex fork release."""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FORK_REPOSITORY = "aaudin90/codex"
FORK_BRANCH = "plan-mode-model-selection"
UPSTREAM_REPOSITORY = "openai/codex"
UPSTREAM_GIT_URL = "https://github.com/openai/codex.git"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-(?:alpha|beta)[A-Za-z0-9.-]*)?$")
FORK_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$")


class CommandFailed(RuntimeError):
    """A subprocess failed after its output was captured."""


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    network: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command))
    environment = os.environ.copy()
    if network:
        environment["NO_PROXY"] = "*"
    result = subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True)
    if check and result.returncode:
        output = (result.stderr or result.stdout).strip()
        raise CommandFailed(f"{' '.join(command)} failed{': ' + output if output else ''}")
    return result


def output(command: list[str], *, cwd: Path, network: bool = False) -> str:
    return run(command, cwd=cwd, network=network).stdout.strip()


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise CommandFailed(f"required command is unavailable: {name}")


def repository_root() -> Path:
    return Path(output(["git", "rev-parse", "--show-toplevel"], cwd=Path.cwd()))


def workspace_version(root: Path) -> str:
    manifest = root / "codex-rs" / "Cargo.toml"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    in_workspace_package = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            in_workspace_package = stripped == "[workspace.package]"
        elif in_workspace_package:
            match = re.match(r'^version\s*=\s*"([^"]+)"\s*$', stripped)
            if match:
                return match.group(1)
    raise CommandFailed(f"could not read [workspace.package].version from {manifest}")


def ensure_clean(root: Path) -> None:
    if output(["git", "status", "--porcelain"], cwd=root):
        raise CommandFailed("worktree is dirty; commit or remove changes before releasing")


def ensure_fork_branch(root: Path) -> None:
    branch = output(["git", "branch", "--show-current"], cwd=root)
    if branch != FORK_BRANCH:
        raise CommandFailed(f"release must run on {FORK_BRANCH}, current branch is {branch or 'detached HEAD'}")


def ensure_ancestor(ancestor: str, root: Path, label: str) -> None:
    result = run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"], cwd=root, check=False)
    if result.returncode:
        raise CommandFailed(f"{label} is not an ancestor of current HEAD")


def exact_upstream_commit(root: Path, upstream_tag: str) -> str:
    ref = json.loads(
        output(
            ["gh", "api", "--method", "GET", f"repos/{UPSTREAM_REPOSITORY}/git/ref/tags/{upstream_tag}"],
            cwd=root,
            network=True,
        )
    )
    object_type = ref["object"]["type"]
    object_sha = ref["object"]["sha"]
    while object_type == "tag":
        tag = json.loads(
            output(
                ["gh", "api", "--method", "GET", f"repos/{UPSTREAM_REPOSITORY}/git/tags/{object_sha}"],
                cwd=root,
                network=True,
            )
        )
        object_type = tag["object"]["type"]
        object_sha = tag["object"]["sha"]
    if object_type != "commit":
        raise CommandFailed(f"upstream tag {upstream_tag} does not resolve to a commit")
    return object_sha


def ensure_upstream_object(root: Path, upstream_tag: str, commit: str) -> None:
    exists = run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root, check=False)
    if exists.returncode:
        run(
            ["git", "fetch", "--no-tags", UPSTREAM_GIT_URL, f"refs/tags/{upstream_tag}"],
            cwd=root,
            network=True,
        )
    fetched = run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root, check=False)
    if fetched.returncode:
        raise CommandFailed(f"could not obtain exact upstream commit {commit} from {upstream_tag}")


def ensure_github_access(root: Path) -> None:
    run(["gh", "auth", "status"], cwd=root, network=True)
    repository = json.loads(
        output(["gh", "api", "--method", "GET", f"repos/{FORK_REPOSITORY}"], cwd=root, network=True)
    )
    if not repository.get("permissions", {}).get("push"):
        raise CommandFailed(f"authenticated GitHub user lacks push permission to {FORK_REPOSITORY}")


def ensure_tag_and_release_absent(root: Path, fork_tag: str) -> None:
    local_tag = run(["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{fork_tag}"], cwd=root, check=False)
    if local_tag.returncode == 0:
        raise CommandFailed(f"local tag already exists: {fork_tag}")
    remote_tag = run(
        ["git", "ls-remote", "--exit-code", "--tags", "origin", f"refs/tags/{fork_tag}"],
        cwd=root,
        network=True,
        check=False,
    )
    if remote_tag.returncode == 0:
        raise CommandFailed(f"remote tag already exists: {fork_tag}")
    release = run(["gh", "release", "view", fork_tag, "--repo", FORK_REPOSITORY], cwd=root, network=True, check=False)
    if release.returncode == 0:
        raise CommandFailed(f"GitHub release already exists: {fork_tag}")


def binary_path(root: Path) -> Path:
    metadata = json.loads(
        output(["cargo", "metadata", "--no-deps", "--format-version", "1"], cwd=root / "codex-rs")
    )
    return Path(metadata["target_directory"]) / "release" / "codex"


def build_artifacts(root: Path, version: str) -> tuple[Path, Path, tempfile.TemporaryDirectory[str]]:
    if sys.platform != "darwin" or platform.machine() not in {"arm64", "aarch64"}:
        raise CommandFailed("publishing a fork release requires a macOS ARM64 host")
    run(["cargo", "build", "--release", "-p", "codex-cli", "--bin", "codex"], cwd=root / "codex-rs")
    lockfile_changed = run(
        ["git", "diff", "--quiet", "--", "codex-rs/Cargo.lock"], cwd=root, check=False
    )
    if lockfile_changed.returncode:
        run(["git", "restore", "--worktree", "--", "codex-rs/Cargo.lock"], cwd=root)
    ensure_clean(root)
    binary = binary_path(root)
    if not binary.is_file():
        raise CommandFailed(f"built binary is missing: {binary}")
    reported_version = output([str(binary), "--version"], cwd=root)
    if version not in reported_version:
        raise CommandFailed(f"codex --version did not contain expected version {version}: {reported_version}")
    artifacts = tempfile.TemporaryDirectory(prefix="codex-fork-release-")
    artifacts_dir = Path(artifacts.name)
    artifact = artifacts_dir / "codex-aarch64-apple-darwin"
    shutil.copy2(binary, artifact)
    checksum = artifacts_dir / f"{artifact.name}.sha256"
    checksum.write_text(
        output(["shasum", "-a", "256", artifact.name], cwd=artifacts_dir) + "\n",
        encoding="utf-8",
    )
    return artifact, checksum, artifacts


def release_notes(root: Path, upstream_tag: str, upstream_commit: str) -> str:
    fork_commit = output(["git", "rev-parse", "HEAD"], cwd=root)
    downstream_log = output(
        ["git", "log", "--oneline", "--max-count", "50", f"{upstream_commit}..HEAD"], cwd=root
    )
    return "\n".join(
        [
            f"Upstream: `{upstream_tag}` (`{upstream_commit}`)",
            f"Fork commit: `{fork_commit}`",
            "",
            "## Downstream changes",
            downstream_log or "No downstream commits.",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Upstream version: X.Y.Z[-alpha…|-beta…]")
    parser.add_argument(
        "--fork-version",
        help="Optional fork release version for fork-v<version>; defaults to the upstream version",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate only (default)")
    mode.add_argument("--publish", action="store_true", help="Create, push, and publish the release")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not VERSION_PATTERN.fullmatch(args.version):
        raise CommandFailed("version must match X.Y.Z[-alpha…|-beta…]")
    fork_version = args.fork_version or args.version
    if not FORK_VERSION_PATTERN.fullmatch(fork_version):
        raise CommandFailed("fork version must match X.Y.Z[-prerelease]")
    for tool in ("git", "gh", "cargo", "shasum"):
        require_tool(tool)
    root = repository_root()
    ensure_fork_branch(root)
    if workspace_version(root) != args.version:
        raise CommandFailed(
            f"codex-rs/Cargo.toml version is {workspace_version(root)}, expected {args.version}; create the version bump first"
        )
    ensure_clean(root)
    ensure_github_access(root)
    upstream_tag = f"rust-v{args.version}"
    upstream_commit = exact_upstream_commit(root, upstream_tag)
    ensure_upstream_object(root, upstream_tag, upstream_commit)
    ensure_ancestor(upstream_commit, root, f"upstream commit {upstream_commit}")
    fork_tag = f"fork-v{fork_version}"
    ensure_tag_and_release_absent(root, fork_tag)
    if not args.publish:
        print(f"dry run succeeded: {fork_tag} would be created at HEAD")
        return 0
    artifact, checksum, artifacts = build_artifacts(root, args.version)
    try:
        run(["git", "tag", "-a", fork_tag, "HEAD", "-m", f"Fork release {fork_tag}"], cwd=root)
        run(["git", "push", "origin", fork_tag], cwd=root, network=True)
        run(
            [
                "gh",
                "release",
                "create",
                fork_tag,
                str(artifact),
                str(checksum),
                "--repo",
                FORK_REPOSITORY,
                "--title",
                f"Codex fork {fork_version}",
                "--notes",
                release_notes(root, upstream_tag, upstream_commit),
            ],
            cwd=root,
            network=True,
        )
    finally:
        artifacts.cleanup()
    print(f"published {fork_tag}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CommandFailed as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
