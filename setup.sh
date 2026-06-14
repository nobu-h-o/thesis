#!/usr/bin/env bash
#
# Scaffold the data/ tiers and fetch the ExeBench train_real_compilable split.
#
#   data/input/<split>/   <- raw .jsonl.zst shards (read-only source)
#   data/build/<split>/   <- cleaned stage1.jsonl (created later by build.ipynb)
#   data/output/<split>/  <- compiled IR / measurements (created later)
#
# Pinned to a fixed dataset revision for reproducibility. Idempotent: skips a
# finished download, resumes a partial one, skips extraction if shards exist.
#
# Run from the repo root:  bash setup_data.sh

set -euo pipefail

SPLIT="${SPLIT:-train_real_compilable}"
REPO="jordiae/exebench"
REVISION="${REVISION:-093085f8558cfd53de8e2c8f4ccc7b9e73dc22ae}"
URL="https://huggingface.co/datasets/${REPO}/resolve/${REVISION}/${SPLIT}.tar.gz"

KEEP_TARBALL=0   # set to 1 to keep the .tar.gz after extraction

DATA_DIR="data"
INPUT_DIR="${DATA_DIR}/input/${SPLIT}"
TARBALL="${DATA_DIR}/input/${SPLIT}.tar.gz"

echo ">> creating directory tiers"
mkdir -p "${DATA_DIR}/input" "${DATA_DIR}/build/${SPLIT}" "${DATA_DIR}/output/${SPLIT}"

# --- skip if already extracted ---
if ls "${INPUT_DIR}"/*.jsonl.zst >/dev/null 2>&1; then
    n=$(ls "${INPUT_DIR}"/*.jsonl.zst | wc -l | tr -d ' ')
    echo ">> ${INPUT_DIR} already has ${n} shards — nothing to do."
    exit 0
fi

# --- download (curl preferred, wget fallback), with resume ---
echo ">> downloading ${SPLIT}.tar.gz (~1.57 GB) from pinned revision ${REVISION:0:7}"
if command -v curl >/dev/null 2>&1; then
    curl -L -C - -o "${TARBALL}" "${URL}"
elif command -v wget >/dev/null 2>&1; then
    wget -c -O "${TARBALL}" "${URL}"
else
    echo "ERROR: need curl or wget" >&2
    exit 1
fi

# --- sanity check: HF sometimes serves an HTML error page as the file ---
if [ "$(wc -c < "${TARBALL}")" -lt 1000000 ]; then
    echo "ERROR: downloaded file is suspiciously small — likely an error page, not the tarball." >&2
    echo "       Check the URL/revision and your network, then delete ${TARBALL} and retry." >&2
    exit 1
fi

# --- extract into data/input (tarball contains the <split>/ dir) ---
echo ">> extracting into ${DATA_DIR}/input/"
tar -xzf "${TARBALL}" -C "${DATA_DIR}/input/"

# --- verify ---
if ls "${INPUT_DIR}"/*.jsonl.zst >/dev/null 2>&1; then
    n=$(ls "${INPUT_DIR}"/*.jsonl.zst | wc -l | tr -d ' ')
    echo ">> OK: ${n} shards in ${INPUT_DIR}"
else
    echo "WARN: no .jsonl.zst found under ${INPUT_DIR} after extraction." >&2
    echo "      The tarball may extract to a different path — inspect ${DATA_DIR}/input/ and move shards into ${INPUT_DIR}/." >&2
    exit 1
fi

# --- cleanup ---
if [ "${KEEP_TARBALL}" -eq 0 ]; then
    echo ">> removing tarball (set KEEP_TARBALL=1 to keep it)"
    rm -f "${TARBALL}"
fi

echo ">> done."