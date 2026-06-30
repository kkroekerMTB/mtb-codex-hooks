#!/usr/bin/env python3
"""Publish and install the Codex logging hooks into a user Codex directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import publish


DEFAULT_CODEX_DIR = Path.home() / ".codex"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run scripts/publish.py with its default output directory, then copy "
            "the published hook artifacts into the Codex install directory."
        )
    )
    parser.add_argument(
        "--codex-dir",
        type=Path,
        default=DEFAULT_CODEX_DIR,
        help="Codex install directory to overwrite. Defaults to ~/.codex.",
    )
    args = parser.parse_args()

    codex_dir = args.codex_dir.expanduser().resolve()
    assert_safe_codex_dir(codex_dir)

    artifact_dir = publish.publish()
    install_artifacts(artifact_dir, codex_dir)

    print(f"Installed Codex logging hooks into {codex_dir}")
    return 0


def assert_safe_codex_dir(codex_dir: Path) -> None:
    if codex_dir == publish.REPO_ROOT:
        raise SystemExit("Refusing to install over the repository root.")
    if codex_dir == publish.REPO_ROOT / ".codex":
        raise SystemExit("Refusing to install over this repository's .codex directory.")


def install_artifacts(source_dir: Path, codex_dir: Path) -> None:
    if not source_dir.is_dir():
        raise SystemExit(f"Published artifact directory does not exist: {source_dir}")

    codex_dir.mkdir(parents=True, exist_ok=True)

    copy_file(source_dir / "hooks.json", codex_dir / "hooks.json")
    copy_directory(source_dir / "hooks", codex_dir / "hooks")


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise SystemExit(f"Expected published file does not exist: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_directory(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"Expected published directory does not exist: {source}")

    if destination.exists():
        if destination.is_dir():
            shutil.rmtree(destination)
        else:
            destination.unlink()

    shutil.copytree(source, destination)


if __name__ == "__main__":
    raise SystemExit(main())
