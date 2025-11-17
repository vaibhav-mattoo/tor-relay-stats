#!/bin/bash
#SBATCH --job-name=tor-bw-network-2024
#SBATCH --output=/work/hdd/bdpr/vmattoo2/tor-relay-stats/slurm_logs/%x_%j.out
#SBATCH --error=/work/hdd/bdpr/vmattoo2/tor-relay-stats/slurm_logs/%x_%j.err
#SBATCH --time=24:00:00
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --account=bdpr-delta-cpu
#SBATCH --mail-user=vmattoo2@illinois.edu
#SBATCH --mail-type=BEGIN,END

set -euo pipefail

PROJECT_DIR="/work/hdd/bdpr/vmattoo2/tor-relay-stats"
LOG_DIR="$PROJECT_DIR/slurm_logs"
VENV_DIR="$PROJECT_DIR/.venv"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

echo "[INFO] Using PROJECT_DIR=$PROJECT_DIR"
echo "[INFO] SLURM_JOB_ID=${SLURM_JOB_ID:-no-slurm}"
echo "[INFO] Hostname: $(hostname)"
echo "[INFO] Starting at: $(date -Is)"

if [ ! -d "$VENV_DIR" ]; then
  echo "[INFO] Creating Python venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -V

echo "[INFO] Installing Python dependencies"
python -m pip install --upgrade pip
python -m pip install numpy matplotlib

export PYTHONUNBUFFERED=1

START_DATE="2024-01-01"
END_DATE="2025-01-01"
OUTPUT_PREFIX="network_2024"

echo "[STEP] Running full-year network analysis"
python "$PROJECT_DIR/analyze_bandwidth.py" \
  "$PROJECT_DIR/bandwidth_data" \
  --network \
  --start-date "$START_DATE" \
  --end-date "$END_DATE" \
  --output-prefix "$OUTPUT_PREFIX"

echo "[DONE] Completed at: $(date -Is)"
