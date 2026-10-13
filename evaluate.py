"""Computes baseline held-out validation metrics on data/val.csv, and
exports held-out test-set predictions to data/test_predictions.csv.

Reports the deterministic Green Home Score distribution, and benchmarks
the valuation engine (src/engines/valuation.py) against two baselines -
a naive mean predictor and a linear OLS regression - on held-out data.
Writes models/baseline_eval_metrics.json and prints a comparison table.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.engines.battle import (
    PACKAGES,
    RETROFIT_CATALOG,
    estimate_package_energy_and_carbon,
    estimate_package_score_uplift,
)
from src.engines.carbon_energy import (
    ELEC_CARBON_FACTOR_KG_PER_KWH,
    GAS_CARBON_FACTOR_KG_PER_KWH,
)
from src.engines.scoring import (
    EpcRating,
    GlazingType,
    build_score_inputs,
    classify_score,
    compute_green_home_score,
    insulation_level_to_condition,
)
from src.engines.valuation import EPC_RANK, estimate_value_uplift

TRAIN_PATH = Path("data/train.csv")
VAL_PATH = Path("data/val.csv")
TEST_PATH = Path("data/test.csv")
OUTPUT_PATH = Path("models/baseline_eval_metrics.json")
TEST_PREDICTIONS_OUTPUT_PATH = Path("data/test_predictions.csv")

TARGET_COLUMN = "target_value_uplift_pct"

# The "recommended retrofits" package used for Deliverable I's held-out
# predictions - the most complete catalog package (P5, Whole-Home
# Net-Zero), matching generate_data.py's own "full retrofit to best
# practice" semantics for its target_value_uplift_pct column.
_PREDICTIONS_PACKAGE_ID = "P5"


def _row_green_home_score(row: pd.Series) -> int:
    result = compute_green_home_score(
        build_score_inputs(
            epc_rating=EpcRating(row["epc_rating"]),
            insulation_level=row["insulation"],
            heating_type=row["heating_type"],
            glazing_type=GlazingType(row["glazing"]),
            solar=bool(row["solar"]),
            smart_controls=bool(row["smart_controls"]),
            elec_kwh=row["baseline_elec_kwh"],
            gas_kwh=row["baseline_gas_kwh"],
            floor_area_m2=row["floor_area"],
        )
    )
    return result.score


def _row_candidate_prediction(row: pd.Series) -> float:
    # target_value_uplift_pct represents the uplift from a full retrofit
    # to best practice (see generate_data.py), not a specific target
    # band, so we evaluate the candidate against target_epc="A" to match
    # that semantic. predicted_uplift_pct is on a 0-100 scale; the target
    # column is a 0-1 fraction, so divide by 100 for a fair comparison.
    result = estimate_value_uplift(
        row["current_value"], row["epc_rating"], target_epc="A"
    )
    return result.predicted_uplift_pct / 100.0


def _regression_metrics(y_true: pd.Series, y_pred) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def _evaluate_valuation_models(train_df: pd.DataFrame, val_df: pd.DataFrame) -> dict:
    y_train = train_df[TARGET_COLUMN]
    y_val = val_df[TARGET_COLUMN]

    # Baseline 1: Naive Mean Predictor - the train-set mean, applied to
    # every held-out row.
    naive_pred = np.full(len(val_df), y_train.mean())
    naive_metrics = _regression_metrics(y_val, naive_pred)

    # Baseline 2: Linear OLS Regression on simple numeric features.
    feature_cols = ["epc_rank", "floor_area", "bedrooms"]
    train_features = train_df.assign(
        epc_rank=train_df["epc_rating"].map(EPC_RANK)
    )[feature_cols]
    val_features = val_df.assign(epc_rank=val_df["epc_rating"].map(EPC_RANK))[
        feature_cols
    ]

    ols = LinearRegression()
    ols.fit(train_features, y_train)
    ols_pred = ols.predict(val_features)
    ols_metrics = _regression_metrics(y_val, ols_pred)

    # Candidate: the system's actual valuation engine - a trained
    # regressor if models/property_value_regressor.pkl exists and loads,
    # else the rule-based model calibrated from data/train.csv.
    candidate_pred = val_df.apply(_row_candidate_prediction, axis=1)
    candidate_metrics = _regression_metrics(y_val, candidate_pred)

    return {
        "naive_mean_predictor": naive_metrics,
        "linear_ols_regression": ols_metrics,
        "candidate_trained_regressor": candidate_metrics,
    }


def _print_comparison_table(results: dict) -> None:
    header = f"{'Model':<28}{'MAE':>10}{'RMSE':>10}{'R2':>10}"
    print(header)
    print("-" * len(header))
    for name, metrics in results.items():
        label = name.replace("_", " ").title()
        print(
            f"{label:<28}{metrics['mae']:>10.4f}{metrics['rmse']:>10.4f}"
            f"{metrics['r2']:>10.4f}"
        )


def evaluate() -> dict:
    train_df = pd.read_csv(TRAIN_PATH)
    val_df = pd.read_csv(VAL_PATH).copy()

    val_df["green_home_score"] = val_df.apply(_row_green_home_score, axis=1)
    valuation_comparison = _evaluate_valuation_models(train_df, val_df)

    metrics = {
        "n_properties": len(val_df),
        "green_home_score_mean": float(val_df["green_home_score"].mean()),
        "green_home_score_std": float(val_df["green_home_score"].std()),
        "valuation_model_comparison": valuation_comparison,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(metrics, indent=2))

    print(
        json.dumps(
            {
                "n_properties": metrics["n_properties"],
                "green_home_score_mean": metrics["green_home_score_mean"],
                "green_home_score_std": metrics["green_home_score_std"],
            },
            indent=2,
        )
    )
    print()
    print(f"Valuation model comparison (target: {TARGET_COLUMN}):")
    _print_comparison_table(valuation_comparison)

    return metrics


def _row_prediction(row: pd.Series) -> dict:
    epc_rating = EpcRating(row["epc_rating"])
    baseline_elec = float(row["baseline_elec_kwh"])
    baseline_gas = float(row["baseline_gas_kwh"])
    floor_area = float(row["floor_area"])

    baseline_result = compute_green_home_score(
        build_score_inputs(
            epc_rating=epc_rating,
            insulation_level=row["insulation"],
            heating_type=row["heating_type"],
            glazing_type=GlazingType(row["glazing"]),
            solar=bool(row["solar"]),
            smart_controls=bool(row["smart_controls"]),
            elec_kwh=baseline_elec,
            gas_kwh=baseline_gas,
            floor_area_m2=floor_area,
        )
    )
    baseline_score = baseline_result.score
    baseline_kwh = baseline_elec + baseline_gas
    baseline_carbon_kg = (
        baseline_elec * ELEC_CARBON_FACTOR_KG_PER_KWH
        + baseline_gas * GAS_CARBON_FACTOR_KG_PER_KWH
    )

    uplift = estimate_package_score_uplift(
        _PREDICTIONS_PACKAGE_ID,
        epc_rating=epc_rating,
        insulation_level=row["insulation"],
        heating_type=row["heating_type"],
        glazing_type=GlazingType(row["glazing"]),
        solar=bool(row["solar"]),
        smart_controls=bool(row["smart_controls"]),
        baseline_elec=baseline_elec,
        baseline_gas=baseline_gas,
        floor_area_m2=floor_area,
    )
    insulation_condition = insulation_level_to_condition(row["insulation"])
    energy = estimate_package_energy_and_carbon(
        _PREDICTIONS_PACKAGE_ID,
        baseline_elec,
        baseline_gas,
        property_features={
            "heating": row["heating_type"],
            "insulation_loft": insulation_condition,
            "insulation_wall": insulation_condition,
            "insulation_floor": insulation_condition,
            "glazing": GlazingType(row["glazing"]),
        },
    )
    potential_score = uplift["after_score"]

    valuation = estimate_value_uplift(
        float(row["current_value"]), row["epc_rating"], target_epc="A"
    )

    recommended_names = [
        RETROFIT_CATALOG[r_id]["name"]
        for r_id in PACKAGES[_PREDICTIONS_PACKAGE_ID]["r_ids"]
    ]

    return {
        "property_id": row["property_id"],
        "epc_rating": row["epc_rating"],
        "baseline_score": baseline_score,
        "baseline_band": classify_score(baseline_score),
        "baseline_purchased_kwh": round(baseline_kwh, 1),
        "baseline_carbon_tonnes": round(baseline_carbon_kg / 1000.0, 3),
        "recommended_retrofits": "; ".join(recommended_names),
        "potential_score": potential_score,
        "potential_band": classify_score(potential_score),
        "net_kwh_saving": round(energy.net_kwh_saving, 1),
        "net_carbon_saving_tonnes": round(energy.carbon_reduction_tonnes, 3),
        "uplift_pct_range": (
            f"{valuation.indicative_range_low_pct:.2f}%-"
            f"{valuation.indicative_range_high_pct:.2f}%"
        ),
        "indicative_value_range_gbp": (
            f"{valuation.indicative_range_low_value:.2f}-"
            f"{valuation.indicative_range_high_value:.2f}"
        ),
    }


def export_test_predictions() -> pd.DataFrame:
    """Deliverable I: held-out test-set predictions. Runs every property
    in data/test.csv through the real scoring/carbon/valuation engines
    (never a trained model guessing the label) and writes the result to
    data/test_predictions.csv."""
    test_df = pd.read_csv(TEST_PATH)
    predictions = pd.DataFrame([_row_prediction(row) for _, row in test_df.iterrows()])
    TEST_PREDICTIONS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(TEST_PREDICTIONS_OUTPUT_PATH, index=False)
    print(f"Wrote {len(predictions)} rows to {TEST_PREDICTIONS_OUTPUT_PATH}")
    return predictions


if __name__ == "__main__":
    evaluate()
    export_test_predictions()
