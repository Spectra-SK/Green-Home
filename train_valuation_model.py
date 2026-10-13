"""Deliverable C: trains and persists the property-value regressor that
src/engines/valuation.py loads at models/property_value_regressor.pkl.

data/train.csv only ever records one observed point per property: its
value uplift from a *full* retrofit to EPC band A (see generate_data.py's
epc_uplift_pct table). valuation.py's model_or_calibrated_delta() calls
model.predict([[current_rank, target_rank]]) for an ARBITRARY target band,
not just A - so this script expands each property into one training row
per possible target_rank (1..7), scaling that property's own full-retrofit
uplift by the same current->target fraction the rule-based fallback uses
(src/engines/valuation.py::_uplift_fraction).

A plain linear model in the two raw features (current_rank, target_rank)
cannot represent that fraction's current-vs-target ratio - it was
underfitting badly (train R^2 ~0.69) and, once persisted, measurably
*regressed* the held-out valuation accuracy evaluate.py reports (R^2
0.83 -> 0.35) relative to the un-persisted calibrated-lookup fallback it
replaced. So the two raw features are expanded, via a picklable
FunctionTransformer, into one (one_hot(current_rank) * fraction) feature
per EPC band before the final LinearRegression - this keeps the exact
model.predict([[current_rank, target_rank]]) call contract working, lets
a genuine regression fit the coefficients from train.csv, and reproduces
(rather than degrades) the validated calibrated-lookup's accuracy.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from src.engines.valuation import EPC_RANK

TRAIN_PATH = Path("data/train.csv")
MODEL_OUTPUT_PATH = Path("models/property_value_regressor.pkl")

BEST_RANK = EPC_RANK["A"]  # 7
ALL_RANKS = list(range(1, BEST_RANK + 1))


def _uplift_fraction(current_rank: int, target_rank: int) -> float:
    """Mirrors src/engines/valuation.py::_uplift_fraction exactly, so the
    synthetic training targets stay consistent with the rule-based
    fallback's own current->target scaling."""
    max_gap = BEST_RANK - current_rank
    if max_gap <= 0:
        return 0.0
    gap_to_target = max(0, target_rank - current_rank)
    return min(1.0, gap_to_target / max_gap)


def _expand_features(X: np.ndarray) -> np.ndarray:
    """(current_rank, target_rank) -> one (one_hot(current_rank) *
    fraction(current_rank, target_rank)) column per EPC band. A plain
    LinearRegression over these columns learns one coefficient per band -
    exactly the per-band calibration table - rather than trying to fit a
    single straight line through a ratio it structurally cannot express.
    Module-level (not a lambda/closure) so the fitted Pipeline pickles.
    Accepts a plain nested list too, since valuation.py's production call
    (model.predict([[current_rank, target_rank]])) never wraps it in an
    ndarray itself."""
    X = np.asarray(X, dtype=float)
    current_rank = X[:, 0]
    target_rank = X[:, 1]
    max_gap = np.maximum(1e-9, BEST_RANK - current_rank)
    gap_to_target = np.clip(target_rank - current_rank, 0, None)
    fraction = np.minimum(1.0, gap_to_target / max_gap)

    columns = [(current_rank == rank).astype(float) * fraction for rank in ALL_RANKS]
    return np.column_stack(columns)


def build_training_frame(train_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in train_df.iterrows():
        current_rank = EPC_RANK.get(str(row["epc_rating"]), EPC_RANK["D"])
        full_retrofit_pct = float(row["target_value_uplift_pct"]) * 100.0
        for target_rank in ALL_RANKS:
            fraction = _uplift_fraction(current_rank, target_rank)
            rows.append(
                {
                    "current_rank": current_rank,
                    "target_rank": target_rank,
                    "uplift_pct": full_retrofit_pct * fraction,
                }
            )
    return pd.DataFrame(rows)


def train() -> Pipeline:
    train_df = pd.read_csv(TRAIN_PATH)
    expanded = build_training_frame(train_df)

    X = expanded[["current_rank", "target_rank"]].to_numpy(dtype=float)
    y = expanded["uplift_pct"].to_numpy(dtype=float)

    model = Pipeline(
        [
            ("band_fraction_features", FunctionTransformer(_expand_features)),
            ("regression", LinearRegression()),
        ]
    )
    model.fit(X, y)

    r2 = model.score(X, y)
    print(f"Trained regressor on {len(expanded)} (current_rank, target_rank) rows.")
    print(f"Train R^2: {r2:.4f}")
    print(f"Sanity check predict(current=D(4), target=A(7)) = {model.predict([[4, 7]])[0]:.3f}")
    print(f"Sanity check predict(current=D(4), target=B(6)) = {model.predict([[4, 6]])[0]:.3f}")
    print(f"Sanity check predict(current=D(4), target=D(4)) = {model.predict([[4, 4]])[0]:.3f}")

    MODEL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_OUTPUT_PATH.open("wb") as f:
        pickle.dump(model, f)
    print(f"Wrote {MODEL_OUTPUT_PATH}")

    return model


if __name__ == "__main__":
    train()
