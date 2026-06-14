#!/usr/bin/env python3
"""Manages shared parameters via .env."""

import re, sys
from pathlib import Path

ROOT       = Path(__file__).parent.parent
ENV_FILE   = ROOT / ".env"
MODELS_DIR = ROOT / "models"

SIZE_MAP = {
    "0.5": "Qwen/Qwen2.5-Coder-0.5B", "0.5b": "Qwen/Qwen2.5-Coder-0.5B",
    "1.5": "Qwen/Qwen2.5-Coder-1.5B", "1.5b": "Qwen/Qwen2.5-Coder-1.5B",
    "3":   "Qwen/Qwen2.5-Coder-3B",   "3b":   "Qwen/Qwen2.5-Coder-3B",
    "7":   "Qwen/Qwen2.5-Coder-7B",   "7b":   "Qwen/Qwen2.5-Coder-7B",
}

_STEM_TO_HF = {v.split("/")[-1]: v for v in SIZE_MAP.values()}


def load_settings():
    if not ENV_FILE.exists():
        sys.exit(f"error: {ENV_FILE} not found\nCopy .env.example to .env first.")
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            env[k.strip()] = v.strip()
    return env


def save_settings(s):
    ENV_FILE.write_text(''.join(f"{k}={v}\n" for k, v in s.items()))


# ── commands ────────────────────────────────────────────────────────────────

def cmd_model(arg):
    key = arg.lower()
    s = load_settings()

    if key in SIZE_MAP:
        s["MODEL"] = SIZE_MAP[key]
        save_settings(s)
        print(f"model → {s['MODEL']}")
    else:
        checkpoint = arg
        seed_m = re.search(r'_seed(\d+)$', checkpoint)
        if seed_m:
            model_name = checkpoint[:seed_m.start()]
            seed       = int(seed_m.group(1))
        else:
            model_name = checkpoint
            seed       = None

        if MODELS_DIR.exists():
            existing = {d.name for d in MODELS_DIR.iterdir() if d.is_dir()}
            if checkpoint not in existing:
                print(f"warning: '{checkpoint}' not found in {MODELS_DIR}")

        hf_id = _STEM_TO_HF.get(model_name, "Qwen/" + model_name)
        s["MODEL"] = hf_id
        if seed is not None:
            s["SEED"] = seed
            print(f"model → {hf_id}  seed → {seed}")
        else:
            print(f"model → {hf_id}")
        save_settings(s)


def cmd_dataset_hash(sha):
    s = load_settings()
    s["REVISION"] = sha
    save_settings(s)
    print(f"dataset-hash → {sha}")


def cmd_split(name):
    s = load_settings()
    s["SPLIT"] = name
    save_settings(s)
    print(f"split → {name}")


def cmd_dataset(number):
    try:
        seed = int(number)
    except ValueError:
        sys.exit(f"error: dataset number must be an integer, got '{number}'")
    s = load_settings()
    s["SEED"] = seed
    save_settings(s)
    print(f"dataset (seed) → {seed}")


def cmd_limit(number):
    try:
        limit = int(number)
    except ValueError:
        sys.exit(f"error: limit must be an integer, got '{number}'")
    s = load_settings()
    s["LIMIT"] = limit
    save_settings(s)
    print(f"limit → {limit}")


def cmd_status():
    s = load_settings()
    print(f"model        : {s['MODEL']}")
    print(f"seed         : {s['SEED']}")
    print(f"dataset hash : {s['REVISION']}")
    print(f"split        : {s.get('SPLIT', '(not set)')}")
    print(f"limit        : {s.get('LIMIT', 3000)}")
    if MODELS_DIR.exists():
        checkpoints = sorted(d.name for d in MODELS_DIR.iterdir() if d.is_dir())
        if checkpoints:
            print(f"models/      : {', '.join(checkpoints)}")


# ── entry point ─────────────────────────────────────────────────────────────

USAGE = """\
usage:
  task model        -- <size|checkpoint>   size: 0.5/1.5/3/7 or 0.5B/1.5B/3B/7B
  task dataset      -- <seed>              seed axis: 0, 1, 2
  task dataset-hash -- <sha>              pin dataset revision
  task split        -- <name>             dataset split for generation notebooks
  task limit        -- <n>               row limit (default 3000)
  task status
"""

def main():
    if len(sys.argv) < 2:
        sys.exit(USAGE)

    cmd = sys.argv[1]

    if cmd == "model":
        if len(sys.argv) < 3:
            sys.exit("usage: nb_params.py model <size_or_checkpoint>")
        cmd_model(sys.argv[2])
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
