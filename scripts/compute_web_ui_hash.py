#!/usr/bin/env python3
"""Compute SHA-256 hash of Hermes web UI source tree.

Mirrors `_compute_web_ui_source_content_hash` in hermes_cli/main.py so the
build stamp can be produced without invoking the full CLI (which would
itself try to rebuild). Used by the post-update dashboard rebuild pipeline
to write $HERMES_HOME/web-ui-build-stamp.json so `hermes dashboard` skips
the local build when our GitHub-Actions-built artifact is already in place.

Usage: python compute_web_ui_hash.py [project_root] [web_dir]
"""
import hashlib
import os
import sys
from pathlib import Path

try:
    from pathspec import PathSpec
except ImportError:
    print("pathspec not installed; run from the Hermes venv or `pip install pathspec`", file=sys.stderr)
    sys.exit(2)


def compute_hash(project_root: Path, web_dir: Path) -> str:
    h = hashlib.sha256()

    def hash_file(path: Path) -> None:
        rel = str(path.relative_to(project_root))
        h.update(rel.encode())
        h.update(b"\0")
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
        except OSError:
            pass
        h.update(b"\0")

    gitignore = project_root / ".gitignore"
    lines: list[str] = []
    if gitignore.is_file():
        lines = gitignore.read_text(encoding="utf-8").splitlines()
    spec = PathSpec.from_lines("gitignore", lines)

    for name in ("package.json", "package-lock.json"):
        p = project_root / name
        if p.is_file():
            rel = str(p.relative_to(project_root))
            if not spec.match_file(rel):
                hash_file(p)

    for dirpath, dirnames, filenames in os.walk(web_dir):
        dirnames[:] = [
            d for d in dirnames
            if not spec.match_file(str((Path(dirpath) / d).relative_to(project_root)))
        ]
        for fn in sorted(filenames):
            fp = Path(dirpath) / fn
            rel = str(fp.relative_to(project_root))
            if not spec.match_file(rel):
                hash_file(fp)

    return h.hexdigest()


if __name__ == "__main__":
    project_root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    web_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "web").resolve()
    if not web_dir.is_absolute():
        web_dir = project_root / web_dir
    print(compute_hash(project_root, web_dir))