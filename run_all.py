"""Single-command submission pipeline.

Sequentially: generates the synthetic dataset if missing, trains the
valuation model artifact if missing, runs the test suite (stopping on
any failure), runs the evaluation script (metrics + held-out test
predictions), then launches the interactive API/dashboard server.

Usage:
    python run_all.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PYTHON = sys.executable

TRAIN_CSV = ROOT / "data" / "train.csv"
VALUATION_MODEL = ROOT / "models" / "property_value_regressor.pkl"


def run(cmd: list[str], label: str) -> None:
    print(f"\n=== {label} ===", flush=True)
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        print(f"\n[run_all] '{label}' failed with exit code {result.returncode}. Stopping.")
        sys.exit(result.returncode)


def main() -> None:
    if not TRAIN_CSV.exists():
        run([PYTHON, "generate_data.py"], "Step a: generating synthetic dataset (data/train.csv missing)")
    else:
        print("\n=== Step a: data/train.csv already present, skipping generate_data.py ===")

    if not VALUATION_MODEL.exists():
        run(
            [PYTHON, "train_valuation_model.py"],
            "Step b: training valuation model (models/property_value_regressor.pkl missing)",
        )
    else:
        print("\n=== Step b: models/property_value_regressor.pkl already present, skipping train_valuation_model.py ===")

    run([PYTHON, "-m", "pytest", "tests/", "-v"], "Step c: running test suite")

    run(
        [PYTHON, "evaluate.py"],
        "Step d: running evaluation (models/baseline_eval_metrics.json + data/test_predictions.csv)",
    )

    print("\n=== Step e: launching interactive server (uvicorn) - press Ctrl+C to stop ===", flush=True)
    subprocess.run(
        [PYTHON, "-m", "uvicorn", "app:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT,
        check=False,
    )


if __name__ == "__main__":
    main()
