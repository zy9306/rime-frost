#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path


EXCLUDED_DIRS = {".git"}


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent
    default_output = project_root / "dist" / f"{project_root.name}.zip"

    parser = argparse.ArgumentParser(
        description="Package this Rime config directory into a zip archive for import."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_output,
        help=f"output zip path, default: {default_output}",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="fail if the output zip already exists",
    )
    return parser.parse_args()


def iter_package_files(root: Path, output: Path):
    output = output.resolve(strict=False)

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name not in EXCLUDED_DIRS)

        current_dir = Path(dirpath)
        for filename in sorted(filenames):
            file_path = current_dir / filename
            if file_path.resolve(strict=False) == output:
                continue
            if file_path.suffix == ".zip" and file_path.parent == output.parent:
                continue

            archive_name = file_path.relative_to(root).as_posix()
            yield file_path, archive_name


def add_symlink(zip_file: zipfile.ZipFile, path: Path, archive_name: str) -> None:
    info = zipfile.ZipInfo(archive_name)
    info.create_system = 3
    info.external_attr = (0o120777 & 0xFFFF) << 16
    zip_file.writestr(info, os.readlink(path))


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent
    output = args.output.expanduser()
    if not output.is_absolute():
        output = root / output
    output = output.resolve(strict=False)

    if args.no_overwrite and output.exists():
        print(f"error: output already exists: {output}", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)

    file_count = 0
    total_bytes = 0
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zip_file:
        for file_path, archive_name in iter_package_files(root, output):
            if file_path.is_symlink():
                add_symlink(zip_file, file_path, archive_name)
            else:
                zip_file.write(file_path, archive_name)
            file_count += 1
            total_bytes += file_path.lstat().st_size

    print(f"created: {output}")
    print(f"files: {file_count}")
    print(f"source bytes: {total_bytes}")
    print(f"zip bytes: {output.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
