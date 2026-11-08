#!/usr/bin/env python3
"""rotate_logs.py - size-based log rotation with gzip compression.

When the log file is larger than --max-bytes it is copied to <file>.1.gz and
then truncated in place ("copytruncate"), so the running application can keep
writing to the same file handle. Older archives shift up (.1.gz -> .2.gz ...)
and anything beyond --keep is deleted.

Usage:
    python3 scripts/rotate_logs.py logs/app.log --max-bytes 1048576 --keep 5
"""
import argparse
import gzip
import shutil
import sys
from datetime import datetime
from pathlib import Path


def log(msg):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} [rotate] {msg}")


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def rotate(path: Path, max_bytes: int, keep: int) -> bool:
    if not path.exists():
        log(f"{path} does not exist, nothing to do")
        return False
    size = path.stat().st_size
    if size <= max_bytes:
        log(f"{path} is {human(size)} (limit {human(max_bytes)}), no rotation needed")
        return False

    log(f"{path} is {human(size)} (limit {human(max_bytes)}), rotating")
    # Drop the oldest archive, then shift the rest up by one.
    oldest = path.with_name(f"{path.name}.{keep}.gz")
    if oldest.exists():
        oldest.unlink()
        log(f"deleted {oldest.name} (retention = {keep})")
    for i in range(keep - 1, 0, -1):
        src = path.with_name(f"{path.name}.{i}.gz")
        if src.exists():
            src.rename(path.with_name(f"{path.name}.{i + 1}.gz"))

    target = path.with_name(f"{path.name}.1.gz")
    with path.open("rb") as fin, gzip.open(target, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    with path.open("r+b") as f:
        f.truncate(0)
    compressed = human(target.stat().st_size)
    log(f"archived to {target.name} ({compressed} compressed), {path.name} truncated")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("logfile", type=Path)
    parser.add_argument("--max-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--keep", type=int, default=5)
    args = parser.parse_args()
    if args.keep < 1:
        parser.error("--keep must be at least 1")
    rotate(args.logfile, args.max_bytes, args.keep)
    archives = sorted(args.logfile.parent.glob(f"{args.logfile.name}.*.gz"))
    log(f"archives now present: {', '.join(a.name for a in archives) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
