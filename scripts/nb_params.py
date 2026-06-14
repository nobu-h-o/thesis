#!/usr/bin/env python3
"""Manages shared parameters across project notebooks."""

import json, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

TRAIN_NBS = [
    ROOT / "notebooks/fine-tuning/train.ipynb",
    ROOT / "notebooks/fine-tuning/train_smoke.ipynb",
]
EVAL_NB   = ROOT / "notebooks/evaluation/evaluation.ipynb"
UPLOAD_NB = ROOT / "notebooks/dataset-generation/upload.ipynb"
MODELS_DIR = ROOT / "models"

# index (1/2/3) and size string (0.5B/1.5B/3B/7B) → HuggingFace model ID
SIZE_MAP = {
    "0.5": "Qwen/Qwen2.5-Coder-0.5B", "0.5b": "Qwen/Qwen2.5-Coder-0.5B",
    "1.5": "Qwen/Qwen2.5-Coder-1.5B", "1.5b": "Qwen/Qwen2.5-Coder-1.5B",
    "3":   "Qwen/Qwen2.5-Coder-3B",   "3b":   "Qwen/Qwen2.5-Coder-3B",
    "7":   "Qwen/Qwen2.5-Coder-7B",   "7b":   "Qwen/Qwen2.5-Coder-7B",
}


def load_nb(path):
    return json.loads(path.read_text())


def save_nb(path, data):
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def update_nb_var(path, pattern, replacement_fn):
    """Replace lines matching pattern in every cell. Returns True if anything changed."""
    data = load_nb(path)
    changed = False
    for cell in data["cells"]:
        for i, line in enumerate(cell["source"]):
            m = re.match(pattern, line)
            if m:
                new_line = replacement_fn(m)
                if new_line != line:
                    cell["source"][i] = new_line
                    changed = True
    if changed:
        save_nb(path, data)
    return changed


def read_nb_var(path, pattern):
    """Return the first capture group of the first matching line in any cell."""
    for cell in load_nb(path)["cells"]:
        for line in cell["source"]:
            m = re.match(pattern, line)
            if m:
                return m.group(1)
    return None


# ── commands ────────────────────────────────────────────────────────────────

def cmd_model(arg):
    key = arg.lower()

    if key in SIZE_MAP:
        hf_path    = SIZE_MAP[key]
        model_stem = hf_path.split("/")[-1]   # e.g. "Qwen2.5-Coder-0.5B"

        # MODEL = "Qwen/..." in training notebooks
        pat  = r'^(MODEL\s*=\s*")([^"]+)("[^\n]*\n?)'
        repl = lambda m, p=hf_path: m.group(1) + p + m.group(3)
        for nb in TRAIN_NBS:
            update_nb_var(nb, pat, repl)

        # MODEL_NAME = "Qwen2.5-..." (stem only) in evaluation notebook
        eval_pat  = r'^(MODEL_NAME\s*=\s*")([^"]+)("[^\n]*\n?)'
        eval_repl = lambda m, s=model_stem: m.group(1) + s + m.group(3)
        update_nb_var(EVAL_NB, eval_pat, eval_repl)

        print(f"model → {hf_path}")

    else:
        # Treat as a fine-tuned checkpoint name from models/
        checkpoint = arg

        # Parse optional "_seed{N}" suffix so we can also update SEED in eval
        seed_m = re.search(r'_seed(\d+)$', checkpoint)
        if seed_m:
            model_name = checkpoint[:seed_m.start()]
            seed       = seed_m.group(1)
        else:
            model_name = checkpoint
            seed       = None

        if MODELS_DIR.exists():
            existing = {d.name for d in MODELS_DIR.iterdir() if d.is_dir()}
            if checkpoint not in existing:
                print(f"warning: '{checkpoint}' not found in {MODELS_DIR}")

        eval_pat  = r'^(MODEL_NAME\s*=\s*")([^"]+)("[^\n]*\n?)'
        eval_repl = lambda m, s=model_name: m.group(1) + s + m.group(3)
        update_nb_var(EVAL_NB, eval_pat, eval_repl)

        if seed is not None:
            seed_pat  = r'^(SEED\s*=\s*)(\d+)([^\n]*\n?)'
            seed_repl = lambda m, v=seed: m.group(1) + v + m.group(3)
            update_nb_var(EVAL_NB, seed_pat, seed_repl)
            print(f"eval model → {model_name}  seed → {seed}")
        else:
            print(f"eval model → {model_name}")


def cmd_dataset_hash(sha):
    pat  = r'^(REVISION\s*=\s*")([^"]+)("[^\n]*\n?)'
    repl = lambda m, h=sha: m.group(1) + h + m.group(3)
    for nb in TRAIN_NBS + [EVAL_NB, UPLOAD_NB]:
        update_nb_var(nb, pat, repl)
    print(f"dataset-hash → {sha}")


def cmd_dataset(number):
    """Set SEED — the numbered axis of the scaling sweep (0, 1, 2)."""
    try:
        seed = int(number)
    except ValueError:
        sys.exit(f"error: dataset number must be an integer, got '{number}'")

    pat  = r'^(SEED\s*=\s*)(\d+)([^\n]*\n?)'
    repl = lambda m, v=str(seed): m.group(1) + v + m.group(3)
    for nb in [TRAIN_NBS[0], EVAL_NB]:
        update_nb_var(nb, pat, repl)
    print(f"dataset (seed) → {seed}")


def cmd_status():
    train_nb = TRAIN_NBS[0]

    model      = read_nb_var(train_nb, r'^MODEL\s*=\s*"([^"]+)"')
    revision   = read_nb_var(train_nb, r'^REVISION\s*=\s*"([^"]+)"')
    seed       = read_nb_var(train_nb, r'^SEED\s*=\s*(\d+)')
    model_name = read_nb_var(EVAL_NB,  r'^MODEL_NAME\s*=\s*"([^"]+)"')

    print(f"model        : {model}")
    print(f"eval model   : {model_name}")
    print(f"dataset hash : {revision}")
    print(f"seed         : {seed}")

    if MODELS_DIR.exists():
        checkpoints = sorted(d.name for d in MODELS_DIR.iterdir() if d.is_dir())
        if checkpoints:
            print(f"models/      : {', '.join(checkpoints)}")


# ── entry point ─────────────────────────────────────────────────────────────

USAGE = """\
usage:
  task model       -- <size|checkpoint>   size: 1/2/3 or 0.5B/1.5B/3B/7B
  task dataset     -- <seed>              seed axis: 0, 1, 2
  task dataset-hash -- <sha>             pin dataset revision
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
    elif cmd == "status":
        cmd_status()
    else:
        sys.exit(f"unknown command: {cmd}\n\n{USAGE}")


if __name__ == "__main__":
    main()
