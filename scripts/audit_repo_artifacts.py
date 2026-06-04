"""Audit tracked and generated research artifacts.

This script is intentionally read-only. It reports files that make the repo
heavy or noisy and prints non-destructive `git rm --cached` commands that can
move generated artifacts out of version control without deleting local copies.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ArtifactGroup:
    name: str
    count: int
    bytes: int
    examples: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-commands",
        action="store_true",
        help="Print git rm --cached commands for tracked generated artifacts.",
    )
    return parser.parse_args()


def git_lines(*args: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return [line for line in completed.stdout.splitlines() if line]


def size_of(relative_path: str) -> int:
    path = ROOT / relative_path
    return path.stat().st_size if path.is_file() else 0


def group(name: str, paths: list[str]) -> ArtifactGroup:
    return ArtifactGroup(
        name=name,
        count=len(paths),
        bytes=sum(size_of(path) for path in paths),
        examples=tuple(paths[:8]),
    )


def shell_quote(path: str) -> str:
    return "'" + path.replace("'", "'\\''") + "'"


def main() -> int:
    args = parse_args()
    tracked = git_lines("ls-files")
    untracked = git_lines("ls-files", "--others", "--exclude-standard")

    tracked_sweeps = [path for path in tracked if path.startswith("sweep_") and path.endswith(".json")]
    tracked_results = [path for path in tracked if path.startswith("results/")]
    tracked_cache = [path for path in tracked_results if "/volume_bar_cvd_cache/" in path]
    untracked_generated = [
        path
        for path in untracked
        if path.startswith(("results/", "data/nautilus/", "logs/"))
        or path in {".KILO_PROJECT_CONTEXT.md", "GEMINI.md"}
    ]

    payload = {
        "repo": str(ROOT),
        "groups": [
            asdict(group("tracked_sweep_json", tracked_sweeps)),
            asdict(group("tracked_results", tracked_results)),
            asdict(group("tracked_volume_bar_cache", tracked_cache)),
            asdict(group("untracked_generated_or_context", untracked_generated)),
        ],
        "notes": [
            "Use git rm --cached to stop tracking generated artifacts without deleting local files.",
            "Keep raw market data and replay caches outside Git unless a tiny fixture is explicitly needed.",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))

    if args.print_commands:
        removable = tracked_sweeps + tracked_results
        if removable:
            quoted = " ".join(shell_quote(path) for path in removable)
            print()
            print("Suggested non-destructive untrack command:")
            print(f"git -C {shell_quote(str(ROOT))} rm --cached -- {quoted}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
