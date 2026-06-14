#!/usr/bin/env python3
"""Manages shared parameters via .env."""

import sys
from pathlib import Path

from dotenv import dotenv_values, set_key

ROOT       = Path(__file__).parent.parent
ENV_FILE   = ROOT / ".env"
MODELS_DIR = ROOT / "models"


def load_settings():
    if not ENV_FILE.exists():
        sys.exit(f"error: {ENV_FILE} not found\nCopy .env.example to .env first.")
    return dotenv_values(ENV_FILE)


def save(key, value):
    set_key(ENV_FILE, key, str(value))


# ── commands ────────────────────────────────────────────────────────────────

SIZE_MAP = {
    "0.5": "Qwen/Qwen2.5-Coder-0.5B", "0.5b": "Qwen/Qwen2.5-Coder-0.5B",
    "1.5": "Qwen/Qwen2.5-Coder-1.5B", "1.5b": "Qwen/Qwen2.5-Coder-1.5B",
    "3":   "Qwen/Qwen2.5-Coder-3B",   "3b":   "Qwen/Qwen2.5-Coder-3B",
    "7":   "Qwen/Qwen2.5-Coder-7B",   "7b":   "Qwen/Qwen2.5-Coder-7B",
}

def cmd_basemodel(arg):
    key = arg.lower()
    if key not in SIZE_MAP:
        sys.exit(f"error: unknown size '{arg}'. Choose from: 0.5, 1.5, 3, 7 (or with B suffix)")
    save("BASEMODEL", SIZE_MAP[key])
    print(f"basemodel → {SIZE_MAP[key]}")


def cmd_dataset_hash(sha):
    save("REVISION", sha)
    print(f"dataset-hash → {sha}")


def cmd_split(name):
    save("SPLIT", name)
    print(f"split → {name}")


def cmd_dataset(number):
    try:
        seed = int(number)
    except ValueError:
        sys.exit(f"error: dataset number must be an integer, got '{number}'")
    save("SEED", seed)
    print(f"dataset (seed) → {seed}")


def cmd_limit(number):
    try:
        limit = int(number)
    except ValueError:
        sys.exit(f"error: limit must be an integer, got '{number}'")
    save("LIMIT", limit)
    print(f"limit → {limit}")


def cmd_status():
    s = load_settings()
    print(f"basemodel    : {s.get('BASEMODEL', '(not set)')}")
    print(f"seed         : {s.get('SEED', '(not set)')}")
    print(f"dataset hash : {s.get('REVISION', '(not set)')}")
    print(f"split        : {s.get('SPLIT', '(not set)')}")
    print(f"limit        : {s.get('LIMIT', 3000)}")
    if MODELS_DIR.exists():
        checkpoints = sorted(d.name for d in MODELS_DIR.iterdir() if d.is_dir())
        if checkpoints:
            print(f"models/      : {', '.join(checkpoints)}")


# ── entry point ─────────────────────────────────────────────────────────────

USAGE = """\
usage:
  task basemodel    -- <size>                0.5, 1.5, 3, 7 (or with B suffix)
  task dataset      -- <seed>                seed axis: 0, 1, 2
  task dataset-hash -- <sha>                 pin dataset revision
  task split        -- <name>                dataset split for generation notebooks
  task limit        -- <n>                   row limit (default 3000)
  task status
"""

def main():
    if len(sys.argv) < 2:
        sys.exit(USAGE)

    cmd = sys.argv[1]

    if cmd == "basemodel":
        if len(sys.argv) < 3:
            sys.exit("usage: nb_params.py basemodel <size>")
        cmd_basemodel(sys.argv[2])
    elif cmd == "dataset-hash":
        if len(sys.argv) < 3:
            sys.exit("usage: nb_params.py dataset-hash <sha>")
        cmd_dataset_hash(sys.argv[2])
    elif cmd == "dataset":
        if len(sys.argv) < 3:
            sys.exit("usage: nb_params.py dataset <number>")
        cmd_dataset(sys.argv[2])
    elif cmd == "split":
        if len(sys.argv) < 3:
            sys.exit("usage: nb_params.py split <name>")
        cmd_split(sys.argv[2])
    elif cmd == "limit":
        if len(sys.argv) < 3:
            sys.exit("usage: nb_params.py limit <n>")
        cmd_limit(sys.argv[2])
    elif cmd == "status":
        cmd_status()
    else:
        sys.exit(f"unknown command: {cmd}\n\n{USAGE}")


if __name__ == "__main__":
    main()
