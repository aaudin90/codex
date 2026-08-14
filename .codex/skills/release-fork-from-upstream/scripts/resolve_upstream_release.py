#!/usr/bin/env python3
"""Resolve an openai/codex rust-v release tag to its exact commit."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys


VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-(?:alpha|beta)[A-Za-z0-9.-]*)?$")
UPSTREAM_REPOSITORY = "openai/codex"


def gh_api(path: str) -> dict[str, object]:
    environment = os.environ.copy()
    environment["NO_PROXY"] = "*"
    result = subprocess.run(
        ["gh", "api", "--method", "GET", path],
        text=True,
        capture_output=True,
        env=environment,
    )
    if result.returncode:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"gh api failed{': ' + message if message else ''}")
    return json.loads(result.stdout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Upstream version: X.Y.Z[-alpha…|-beta…]")
    parser.add_argument("--json", action="store_true", help="Print tag and commit as JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not VERSION_PATTERN.fullmatch(args.version):
        raise RuntimeError("version must match X.Y.Z[-alpha…|-beta…]")
    if shutil.which("gh") is None:
        raise RuntimeError("required command is unavailable: gh")
    tag_name = f"rust-v{args.version}"
    reference = gh_api(f"repos/{UPSTREAM_REPOSITORY}/git/ref/tags/{tag_name}")
    tagged_object = reference["object"]
    object_type = tagged_object["type"]
    object_sha = tagged_object["sha"]
    while object_type == "tag":
        tag = gh_api(f"repos/{UPSTREAM_REPOSITORY}/git/tags/{object_sha}")
        tagged_object = tag["object"]
        object_type = tagged_object["type"]
        object_sha = tagged_object["sha"]
    if object_type != "commit":
        raise RuntimeError(f"upstream tag {tag_name} does not resolve to a commit")
    if args.json:
        print(json.dumps({"tag": tag_name, "commit": object_sha}))
    else:
        print(object_sha)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
