#!/usr/bin/env python3
"""Report or remove bounded Rust build artifacts and caches."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SCOPES = ("project", "cargo-cache", "rustup-cache", "sccache", "all")


@dataclass(frozen=True)
class Candidate:
    category: str
    path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Rust workspace for project artifacts")
    parser.add_argument("--scope", choices=SCOPES, default="all", help="Artifacts to inspect")
    parser.add_argument("--apply", action="store_true", help="Remove reported candidates")
    parser.add_argument("--include-toolchains", action="store_true", help="Also report rustup toolchains")
    parser.add_argument(
        "--confirm-toolchain-removal",
        action="store_true",
        help="Required with --apply --include-toolchains",
    )
    return parser.parse_args()


def command_output(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(command)} failed{': ' + message if message else ''}")
    return result.stdout


def cargo_home() -> Path:
    return Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo"))


def rustup_home() -> Path:
    return Path(os.environ.get("RUSTUP_HOME", Path.home() / ".rustup"))


def project_target_directory(workspace: Path) -> Path:
    metadata = json.loads(
        command_output(["cargo", "metadata", "--no-deps", "--format-version", "1"], workspace)
    )
    return Path(metadata["target_directory"])


def requested(scope: str, candidate_scope: str) -> bool:
    return scope == "all" or scope == candidate_scope


def candidates(args: argparse.Namespace) -> list[Candidate]:
    cargo = cargo_home()
    rustup = rustup_home()
    result: list[Candidate] = []
    if requested(args.scope, "project"):
        result.append(Candidate("project build artifacts", project_target_directory(args.workspace)))
    if requested(args.scope, "cargo-cache"):
        for relative_path in (
            "registry/cache",
            "registry/src",
            "registry/index",
            "git/checkouts",
            "git/db",
            ".package-cache",
        ):
            result.append(Candidate("Cargo cache", cargo / relative_path))
    if requested(args.scope, "rustup-cache"):
        for relative_path in ("downloads", "tmp"):
            result.append(Candidate("rustup download cache", rustup / relative_path))
    if requested(args.scope, "sccache"):
        configured = os.environ.get("SCCACHE_DIR")
        locations = [Path(configured)] if configured else []
        locations.extend((Path.home() / ".cache" / "sccache", Path.home() / "Library" / "Caches" / "sccache"))
        result.extend(Candidate("sccache", location) for location in locations)
    if args.include_toolchains:
        result.append(Candidate("installed rustup toolchains", rustup / "toolchains"))
    return unique_existing_directories(result)


def unique_existing_directories(candidates: list[Candidate]) -> list[Candidate]:
    seen: set[Path] = set()
    result = []
    for candidate in candidates:
        if candidate.path.is_symlink() or not candidate.path.is_dir():
            continue
        resolved = candidate.path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            result.append(Candidate(candidate.category, resolved))
    return result


def directory_size(path: Path) -> int:
    total = 0
    for directory, _, files in os.walk(path):
        for name in files:
            file_path = Path(directory) / name
            try:
                total += file_path.stat().st_size
            except OSError:
                pass
    return total


def readable_size(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("units are exhaustive")


def ensure_safe_to_delete(candidate: Candidate) -> None:
    home = Path.home().resolve()
    protected = {home, cargo_home().resolve(), rustup_home().resolve()}
    if candidate.path in protected or candidate.path.parent == home:
        raise RuntimeError(f"refusing to remove protected directory: {candidate.path}")
    if candidate.path.is_symlink() or not candidate.path.is_dir():
        raise RuntimeError(f"refusing to remove non-directory or symlink: {candidate.path}")


def main() -> int:
    args = parse_args()
    if args.apply and args.include_toolchains and not args.confirm_toolchain_removal:
        raise RuntimeError("--apply --include-toolchains requires --confirm-toolchain-removal")
    if args.apply and not args.include_toolchains and args.confirm_toolchain_removal:
        raise RuntimeError("--confirm-toolchain-removal requires --include-toolchains")
    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        raise RuntimeError(f"workspace is not a directory: {workspace}")
    args.workspace = workspace
    selected = candidates(args)
    if not selected:
        print("No Rust artifact or cache directories found for this scope.")
        return 0
    sizes = [(candidate, directory_size(candidate.path)) for candidate in selected]
    for candidate, size in sizes:
        print(f"{candidate.category}: {candidate.path} ({readable_size(size)})")
    total = sum(size for _, size in sizes)
    print(f"Total reclaimable: {readable_size(total)}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to remove exactly these paths.")
        return 0
    for candidate, _ in sizes:
        ensure_safe_to_delete(candidate)
    for candidate, _ in sizes:
        shutil.rmtree(candidate.path)
        print(f"Removed: {candidate.path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
