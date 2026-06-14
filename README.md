# C → LLVM IR Compilation via Fine-Tuned LLMs

Thesis project: a scaling study that fine-tunes Qwen2.5-Coder (0.5B–7B) to translate C source code into LLVM IR at `-O3`, then measures exact-match and token-similarity across model sizes and random seeds.

## Pipeline

```
ExeBench (HuggingFace)
  └─ download         task download-c-dataset
  └─ build            notebooks/dataset-generation/build.ipynb
  └─ generate_pairs   notebooks/dataset-generation/generate_pairs.ipynb
  └─ upload           notebooks/dataset-generation/upload.ipynb
        │
        ▼
  notoh/exebench_llvm_o3  (HuggingFace dataset)
        │
        ▼
  fine-tuning         notebooks/fine-tuning/train.ipynb
        │
        ▼
  models/<model>_seed<seed>/
        │
        ▼
  evaluation          notebooks/evaluation/evaluation.ipynb
        │
        ▼
  results/<model>_seed<seed>.json
```

## Prerequisites

- Python 3.12+ and [uv](https://github.com/astral-sh/uv)
- [Task](https://taskfile.dev) (`brew install go-task`)
- Clang 22.1.7 at `/opt/homebrew/opt/llvm/bin/clang` (dataset generation only)
- A HuggingFace account with write access (dataset/model upload)
- GPU (training is tested on an L40S via Nebius; see `infra/`)

## Setup

```bash
cp .env.example .env       # fill in HF_TOKEN
uv sync
task status                # confirm .env is loaded
```

## Task commands

| Command | Description |
|---|---|
| `task status` | Show current model, seed, dataset hash, and split |
| `task basemodel -- 0.5` | Switch base model size (0.5, 1.5, 3, 7) |
| `task dataset -- 1` | Set seed (0, 1, 2) |
| `task dataset-hash -- <sha>` | Pin dataset revision SHA |
| `task split -- train_real_compilable` | Set dataset split for generation |
| `task limit -- 3000` | Row limit for dataset generation |
| `task download-c-dataset` | Download ExeBench split from HuggingFace |

## Dataset generation

Run the three notebooks in order:

1. **`build.ipynb`** — unpacks ExeBench `.jsonl.zst` shards into `data/build/<split>/stage1.jsonl`
2. **`generate_pairs.ipynb`** — compiles each function at `-O0` (gate: ≥30 instructions + branch), then at `-O3`, and writes `(C source, O3 IR)` pairs to `data/output/<split>/pairs.jsonl`
3. **`upload.ipynb`** — pushes `pairs.jsonl` to HuggingFace as `notoh/exebench_llvm_o3`

## Training

```bash
task basemodel -- 0.5   # pick model size
task dataset -- 0       # pick seed
```

Then run **`notebooks/fine-tuning/train.ipynb`**.

Weights, tokenizer, `train_log.csv`, and `run_config.json` are written to `models/<model>_seed<seed>/`.

Use `train_smoke.ipynb` to validate the loop on a small subset before committing GPU time.

## Evaluation

Run **`notebooks/evaluation/evaluation.ipynb`** with the same `BASEMODEL` and `SEED` set.

Set `EVAL_MODE = "local"` (default) to evaluate a local checkpoint, or `"hf"` to evaluate any HuggingFace model ID.

Results are written to `results/<stem>.json` and include:

| Metric | Description |
|---|---|
| `exact_match` | Fraction of predictions identical to the reference (after whitespace normalization) |
| `token_sim_mean` | Mean SequenceMatcher ratio over tokenized predictions |
| `eos_rate` | Fraction of predictions that terminated with EOS (diagnostic) |
| `len_ratio_mean` | Mean predicted/reference length ratio; 1.0 = correct length |

## Reproducibility

Every training and eval run is fully determined by four values in `.env`:

| Variable | Role |
|---|---|
| `BASEMODEL` | HuggingFace model ID (size axis) |
| `SEED` | Random seed (seed axis, 0–2) |
| `REVISION` | Pinned dataset commit SHA |
| `SPLIT` | Dataset split name |

Use `task basemodel`, `task dataset`, `task dataset-hash`, and `task split` to change them — these commands update `.env` in place so the values stay consistent across all notebooks.

## Cloud infrastructure

`infra/nebius.tf` provisions a preemptible L40S GPU VM on Nebius AI. Start/stop it manually to control cost. The VM is set to `stopped = true` by default.

## Directory layout

```
notebooks/
  dataset-generation/   build, generate_pairs, upload
  fine-tuning/          train, train_smoke, upload
  evaluation/           evaluation
  sample/               scratch / exploratory notebooks
scripts/
  nb_params.py          reads and writes .env (used by Taskfile)
  download_dataset.py   resumable download of ExeBench splits
infra/
  nebius.tf             Terraform config for GPU VM
data/                   (gitignored) input shards, build artifacts, output pairs
models/                 (gitignored) fine-tuned checkpoints
results/                evaluation JSON files
```
