# Spectra_07

## Prerequisites

- Python 3.11+
- `pip`

## Setup

```
pip install -r requirements.txt
cp .env.example .env   # then fill in GEMINI_API_KEY
```

## Single-Command Execution

# macOS / Linux / Activated Virtual Environment
python run_all.py

# Windows (if python alias is unmapped)
py run_all.py

Runs, in order: dataset generation (if `data/train.csv` is missing),
valuation-model training (if `models/property_value_regressor.pkl` is
missing), the test suite, the evaluation script, then starts the server at
`http://127.0.0.1:8000`. Press `Ctrl+C` to stop the server.

## Individual Step Commands

```
python generate_data.py
python train_valuation_model.py
pytest tests/ -v
ruff check .
python evaluate.py
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

## Submission Artifact Paths

```
data/train.csv
data/val.csv
data/test.csv
data/test_predictions.csv
models/property_value_regressor.pkl
models/baseline_eval_metrics.json
models/llm_eval_results.json
docs/SUBMISSION_DELIVERABLES.md
deliverables/
LICENSE
```
