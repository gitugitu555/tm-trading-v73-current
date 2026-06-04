#!/usr/bin/env python3
"""Manage raw Binance datasets across cold storage and hot cache roots."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.dataset_layout import DatasetSpec, dataset_path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOT_ROOT = Path(os.environ.get("TM_DATA_HOT_ROOT", REPO_ROOT / "data/raw"))
DEFAULT_COLD_ROOT = Path(os.environ.get("TM_DATA_COLD_ROOT", "/mnt/seagate/tm-trading-v555/data/raw"))


@dataclass(frozen=True)
class DatasetRoots:
    hot: Path
    cold: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--market", required=True)
    parser.add_argument("--kind", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--range-label", required=True)
    parser.add_argument("--hot-root", type=Path, default=DEFAULT_HOT_ROOT)
    parser.add_argument("--cold-root", type=Path, default=DEFAULT_COLD_ROOT)

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("path", help="Print canonical hot and cold paths.")
    subparsers.add_parser("status", help="Summarize the hot and cold dataset state.")

    promote = subparsers.add_parser(
        "promote",
        help="Move a hot-cache dataset to cold storage and replace the hot path with a symlink.",
    )
    promote.add_argument("--dry-run", action="store_true", default=False)

    link = subparsers.add_parser(
        "link",
        help="Replace the hot-cache path with a symlink to the cold-storage dataset.",
    )
    link.add_argument("--force", action="store_true", default=False)

    sync = subparsers.add_parser(
        "sync",
        help="Mirror one root to the other with rsync.",
    )
    sync.add_argument(
        "--direction",
        choices=["cold-to-hot", "hot-to-cold"],
        default="cold-to-hot",
    )
    sync.add_argument("--delete", action="store_true", default=False)
    sync.add_argument("--dry-run", action="store_true", default=False)

    return parser.parse_args()


def build_spec(args: argparse.Namespace) -> DatasetSpec:
    return DatasetSpec(
        exchange=args.exchange,
        market=args.market,
        kind=args.kind,
        symbol=args.symbol,
        range_label=args.range_label,
    )


def get_roots(args: argparse.Namespace) -> DatasetRoots:
    return DatasetRoots(hot=args.hot_root, cold=args.cold_root)


def format_status_line(label: str, path: Path) -> str:
    if path.is_symlink():
        return f"{label}: {path} -> {path.resolve()}"
    return f"{label}: {path}"


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def count_files(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for item in path.iterdir() if item.is_file())


def du_sh(path: Path) -> str | None:
    if not path.exists():
        return None
    du = shutil.which("du")
    if du is None:
        return None
    completed = subprocess.run([du, "-sh", str(path)], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.split()[0] if completed.stdout else None


def print_path_pair(spec: DatasetSpec, roots: DatasetRoots) -> None:
    hot = dataset_path(roots.hot, spec)
    cold = dataset_path(roots.cold, spec)
    print(f"relative: {spec.relative_path()}")
    print(f"hot: {hot}")
    print(f"cold: {cold}")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def rsync(
    source: Path,
    target: Path,
    *,
    delete: bool,
    dry_run: bool,
    remove_source_files: bool = False,
) -> None:
    if shutil.which("rsync") is None:
        raise SystemExit("rsync is required for sync/promote operations")

    cmd = ["rsync", "-a"]
    if delete:
        cmd.append("--delete")
    if remove_source_files:
        cmd.append("--remove-source-files")
    if dry_run:
        cmd.append("--dry-run")
    cmd.extend([f"{source}/", f"{target}/"])
    subprocess.run(cmd, check=True)


def prune_empty_dirs(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        return

    for child in sorted(path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if child.is_dir():
            try:
                child.rmdir()
            except OSError:
                pass


def promote_dataset(spec: DatasetSpec, roots: DatasetRoots, *, dry_run: bool) -> None:
    hot_path = dataset_path(roots.hot, spec)
    cold_path = dataset_path(roots.cold, spec)

    if hot_path.is_symlink() and hot_path.resolve() == cold_path.resolve():
        print(f"already promoted: {hot_path}")
        return

    if not hot_path.exists():
        raise SystemExit(f"hot dataset does not exist: {hot_path}")

    ensure_parent(cold_path)
    rsync(hot_path, cold_path, delete=False, dry_run=dry_run, remove_source_files=True)

    if dry_run:
        print(f"dry-run: would move {hot_path} -> {cold_path} and link hot to cold")
        return

    prune_empty_dirs(hot_path)
    if hot_path.exists() and hot_path.is_dir():
        try:
            hot_path.rmdir()
        except OSError:
            pass
    if hot_path.exists() or hot_path.is_symlink():
        if hot_path.is_symlink():
            hot_path.unlink()
        else:
            raise SystemExit(f"hot dataset still exists after promote: {hot_path}")
    hot_path.parent.mkdir(parents=True, exist_ok=True)
    hot_path.symlink_to(cold_path)
    print(f"promoted {hot_path} -> {cold_path}")


def link_dataset(spec: DatasetSpec, roots: DatasetRoots, *, force: bool) -> None:
    hot_path = dataset_path(roots.hot, spec)
    cold_path = dataset_path(roots.cold, spec)

    if not cold_path.exists():
        raise SystemExit(f"cold dataset does not exist: {cold_path}")

    if hot_path.is_symlink() and hot_path.resolve() == cold_path.resolve():
        print(f"already linked: {hot_path}")
        return

    if path_exists(hot_path):
        if not force:
            raise SystemExit(f"hot path already exists: {hot_path} (use --force to replace it)")
        if hot_path.is_symlink() or hot_path.is_file():
            hot_path.unlink()
        else:
            shutil.rmtree(hot_path)

    hot_path.parent.mkdir(parents=True, exist_ok=True)
    hot_path.symlink_to(cold_path)
    print(f"linked {hot_path} -> {cold_path}")


def sync_dataset(spec: DatasetSpec, roots: DatasetRoots, *, direction: str, delete: bool, dry_run: bool) -> None:
    hot_path = dataset_path(roots.hot, spec)
    cold_path = dataset_path(roots.cold, spec)
    if direction == "cold-to-hot":
        source, target = cold_path, hot_path
    else:
        source, target = hot_path, cold_path

    if not source.exists():
        raise SystemExit(f"source dataset does not exist: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
    rsync(source, target, delete=delete, dry_run=dry_run)
    print(f"sync complete: {source} -> {target}")


def status(spec: DatasetSpec, roots: DatasetRoots) -> None:
    hot_path = dataset_path(roots.hot, spec)
    cold_path = dataset_path(roots.cold, spec)
    print(f"dataset: {spec.exchange}/{spec.market}/{spec.kind}/{spec.symbol}/{spec.range_label}")
    print(format_status_line("hot", hot_path))
    print(format_status_line("cold", cold_path))
    print(f"hot_exists: {path_exists(hot_path)}")
    print(f"cold_exists: {path_exists(cold_path)}")
    print(f"hot_files: {count_files(hot_path)}")
    print(f"cold_files: {count_files(cold_path)}")
    hot_size = du_sh(hot_path)
    cold_size = du_sh(cold_path)
    if hot_size is not None:
        print(f"hot_size: {hot_size}")
    if cold_size is not None:
        print(f"cold_size: {cold_size}")


def main() -> int:
    args = parse_args()
    spec = build_spec(args)
    roots = get_roots(args)

    if args.command == "path":
        print_path_pair(spec, roots)
        return 0

    if args.command == "status":
        status(spec, roots)
        return 0

    if args.command == "promote":
        promote_dataset(spec, roots, dry_run=args.dry_run)
        return 0

    if args.command == "link":
        link_dataset(spec, roots, force=args.force)
        return 0

    if args.command == "sync":
        sync_dataset(
            spec,
            roots,
            direction=args.direction,
            delete=args.delete,
            dry_run=args.dry_run,
        )
        return 0

    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
