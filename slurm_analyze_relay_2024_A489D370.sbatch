#!/bin/bash
#SBATCH --job-name=tor-bw-relay-A489D370
#SBATCH --output=/work/hdd/bdpr/vmattoo2/tor-relay-stats/slurm_logs/%x_%j.out
#SBATCH --error=/work/hdd/bdpr/vmattoo2/tor-relay-stats/slurm_logs/%x_%j.err
#SBATCH --time=12:00:00
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --account=bdpr-delta-cpu
#SBATCH --mail-user=vmattoo2@illinois.edu
#SBATCH --mail-type=BEGIN,END

set -euo pipefail

# Project directories
PROJECT_DIR="/work/hdd/bdpr/vmattoo2/tor-relay-stats"
LOG_DIR="$PROJECT_DIR/slurm_logs"
VENV_DIR="$PROJECT_DIR/.venv"

# Relay fingerprint (40 hex chars)
RELAY_FP="A489D37070A5081D814C1F112139EEF0DDC03A48"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

echo "[INFO] Using PROJECT_DIR=$PROJECT_DIR"
echo "[INFO] SLURM_JOB_ID=${SLURM_JOB_ID:-no-slurm}"
echo "[INFO] Hostname: $(hostname)"
echo "[INFO] Starting at: $(date -Is)"

echo "[INFO] Relay fingerprint: $RELAY_FP"

# Set up Python virtual environment (if not already present)
if [ ! -d "$VENV_DIR" ]; then
  echo "[INFO] Creating Python venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -V

# Ensure required packages are installed
echo "[INFO] Installing Python dependencies"
python -m pip install --upgrade pip
python -m pip install numpy matplotlib

export PYTHONUNBUFFERED=1

# Incremental relay-specific analysis
echo "[STEP] Running relay analysis for 2024 (incremental)"
python "$PROJECT_DIR/analyze_bandwidth.py" "$PROJECT_DIR/bandwidth_data" "$RELAY_FP"

echo "[DONE] Completed at: $(date -Is)"
