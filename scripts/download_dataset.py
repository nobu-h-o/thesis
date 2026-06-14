#!/usr/bin/env python3
"""Download a dataset split from HuggingFace into data/input/<split>/."""

import sys
import tarfile
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

REPO = "jordiae/exebench"
DEFAULT_SPLIT = "train_real_compilable"
DEFAULT_REVISION = "093085f8558cfd53de8e2c8f4ccc7b9e73dc22ae"
MIN_BYTES = 1_000_000


def download(url: str, dest: Path) -> None:
    existing = dest.stat().st_size if dest.exists() else 0
    req = urllib.request.Request(url)
    if existing:
        req.add_header("Range", f"bytes={existing}-")
    try:
        resp = urllib.request.urlopen(req)
        mode = "ab" if resp.getcode() == 206 else "wb"
    except urllib.error.HTTPError as e:
        if e.code == 416:
            print(">> resume: server says file is already complete")
            return
        raise
    total = int(resp.headers.get("Content-Length", 0) or 0) + existing
    downloaded = existing
    with open(dest, mode) as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                print(f"\r>> {downloaded / 1e9:.2f} / {total / 1e9:.2f} GB ({downloaded / total * 100:.1f}%)", end="", flush=True)
    print()


def main():
    split    = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SPLIT
    revision = DEFAULT_REVISION

    input_dir = DATA_DIR / "input" / split
    tarball   = DATA_DIR / "input" / f"{split}.tar.gz"
    url       = f"https://huggingface.co/datasets/{REPO}/resolve/{revision}/{split}.tar.gz"

    print(">> creating directory tiers")
    for d in [DATA_DIR / "input", DATA_DIR / "build" / split, DATA_DIR / "output" / split]:
        d.mkdir(parents=True, exist_ok=True)

    shards = list(input_dir.glob("*.jsonl.zst"))
    if shards:
        print(f">> {input_dir} already has {len(shards)} shards — nothing to do.")
        return

    print(f">> downloading {split}.tar.gz (~1.57 GB) from pinned revision {revision[:7]}")
    download(url, tarball)

    if tarball.stat().st_size < MIN_BYTES:
        sys.exit(
            f"error: downloaded file is suspiciously small — likely an error page.\n"
            f"       delete {tarball} and retry."
        )

    print(f">> extracting into {DATA_DIR / 'input'}/")
    with tarfile.open(tarball) as tf:
        tf.extractall(DATA_DIR / "input")

    shards = list(input_dir.glob("*.jsonl.zst"))
    if not shards:
        sys.exit(
            f"warn: no .jsonl.zst found under {input_dir} after extraction.\n"
            f"      inspect {DATA_DIR / 'input'} and move shards manually."
        )
    print(f">> OK: {len(shards)} shards in {input_dir}")

    tarball.unlink()
    print(">> done.")


if __name__ == "__main__":
    main()
