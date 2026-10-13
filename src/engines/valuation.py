"""Property value uplift estimation: before-vs-after a Green Home retrofit.

Prefers a trained regressor at models/property_value_regressor.pkl when
present and loadable; otherwise falls back to a rule-based model
calibrated directly from the observed target_value_uplift_pct
distribution in data/train.csv (or a hardcoded fallback matching that
same distribution, if train.csv isn't available). Always returns an
indicative RANGE, never a single guaranteed figure - this is never a
commercial valuation guarantee.

All percentages in this module (predicted_uplift_pct, the range bounds,
the calibration table) are on a 0-100 scale, not a 0-1 fraction.
"""

import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel

MODEL_PATH = Path("models/property_value_regressor.pkl")
TRAIN_DATA_PATH = Path("data/train.csv")

DEFAULT_TARGET_EPC = "B"

# Fixed, conservative bounds around the point estimate (percentage
# points, not calibrated from data) - a deliberately simple uncertainty
# band rather than a statistically derived one.
RANGE_LOW_OFFSET_PCT = 1.5
RANGE_HIGH_OFFSET_PCT = 1.8

DISCLAIMER = (
    "Indicative statistical estimate based on UK hedonic price baselines. "
    "Not a commercial guarantee or causal proof of future sale price."
)

# Best (A) to worst (G), used to scale a full-retrofit uplift down to
# whatever fraction of the EPC gap current -> target actually covers.
EPC_RANK: dict[str, int] = {"A": 7, "B": 6, "C": 5, "D": 4, "E": 3, "F": 2, "G": 1}

# Fallback calibration (mean % uplift from a full retrofit, 0-100 scale)
# if data/train.csv isn't available (e.g. before generate_data.py has
# been run). Matches generate_data.py's own epc_uplift_pct table.
_FALLBACK_CALIBRATION_PCT: dict[str, float] = {
    "A": 1.30,
    "B": 2.04,
    "C": 3.49,
    "D": 5.04,
    "E": 6.41,
    "F": 8.01,
    "G": 9.54,
}

_calibration_cache: dict[str, float] | None = None
_UNSET: Any = object()
_model_cache: Any = _UNSET


class ValuationResult(BaseModel):
    current_value: float
    post_retrofit_value: float
    predicted_uplift_value: float
    predicted_uplift_pct: float
    indicative_range_low_value: float
    indicative_range_high_value: float
    indicative_range_low_pct: float
    indicative_range_high_pct: float
    disclaimer: str


def _load_calibration() -> dict[str, float]:
    """Mean target_value_uplift_pct per EPC band, from train.csv,
    expressed as a percent (0-100 scale)."""
    global _calibration_cache
    if _calibration_cache is not None:
        return _calibration_cache

    calibration = dict(_FALLBACK_CALIBRATION_PCT)
    try:
        df = pd.read_csv(TRAIN_DATA_PATH)
        means = df.groupby("epc_rating")["target_value_uplift_pct"].mean()
        for epc, mean_fraction in means.items():
            # train.csv's target_value_uplift_pct is always a 0-1 fraction
            # (e.g. 0.0324), so this *100 is normally correct; the `< 1.0`
            # guard just protects against a future train.csv that stores
            # already-scaled percentages instead, without changing today's
            # output for any real fraction value.
            val = float(mean_fraction)
            calibration[str(epc)] = val * 100.0 if val < 1.0 else val
    except (FileNotFoundError, KeyError, ValueError):
        pass

    _calibration_cache = calibration
    return calibration


def _load_model() -> Any:
    """Load models/property_value_regressor.pkl if it exists and is
    loadable; returns None (and stays None) otherwise."""
    global _model_cache
    if _model_cache is not _UNSET:
        return _model_cache

    if MODEL_PATH.exists():
        try:
            with MODEL_PATH.open("rb") as f:
                _model_cache = pickle.load(f)
        except Exception:  # noqa: BLE001 - never let a bad artifact crash scoring
            _model_cache = None
    else:
        _model_cache = None
    return _model_cache


def _uplift_fraction(current_epc: str, target_epc: str) -> float:
    """How much of the current -> A gap the current -> target move covers."""
    current_rank = EPC_RANK.get(current_epc, EPC_RANK["D"])
    target_rank = EPC_RANK.get(target_epc, EPC_RANK[DEFAULT_TARGET_EPC])
    best_rank = EPC_RANK["A"]

    max_gap = best_rank - current_rank
    if max_gap <= 0:
        return 0.0

    gap_to_target = max(0, target_rank - current_rank)
    return min(1.0, gap_to_target / max_gap)


def _rule_based_delta_pct(current_epc: str, target_epc: str) -> float:
    """Calibrated uplift percentage (0-100 scale) for the current ->
    target EPC band shift, scaled by how much of the current band's full
    retrofit potential that specific move covers."""
    calibration = _load_calibration()
    base_pct = calibration.get(
        current_epc, _FALLBACK_CALIBRATION_PCT.get(current_epc, 0.0)
    )
    fraction = _uplift_fraction(current_epc, target_epc)
    return base_pct * fraction


def model_or_calibrated_delta(
    current_epc: str, target_epc: str, property_features: dict | None = None
) -> float:
    """Predicted uplift percentage (0-100 scale) for the current_epc ->
    target_epc band shift. Uses the trained regressor at
    models/property_value_regressor.pkl if it loads and predicts
    successfully; otherwise falls back to the train.csv-calibrated,
    rank-scaled delta.

    `property_features` is accepted for forward compatibility with a
    richer trained regressor - the rule-based fallback does not use it.
    """
    model = _load_model()
    if model is not None:
        try:
            current_rank = EPC_RANK.get(current_epc, EPC_RANK["D"])
            target_rank = EPC_RANK.get(target_epc, EPC_RANK[DEFAULT_TARGET_EPC])
            return float(model.predict([[current_rank, target_rank]])[0])
        except Exception:  # noqa: BLE001, S110 - never let a bad artifact crash scoring
            pass
    return _rule_based_delta_pct(current_epc, target_epc)


def estimate_value_uplift(
    current_value: float,
    current_epc: str,
    target_epc: str | None = None,
    property_features: dict | None = None,
) -> ValuationResult:
    """Before-vs-after property value uplift for an EPC band shift.

    `target_epc` defaults to DEFAULT_TARGET_EPC ('B') when omitted.
    `property_features` describes the proposed retrofit scenario and is
    passed through to `model_or_calibrated_delta` for a future, richer
    trained regressor; see that function's docstring for why today's
    rule-based fallback ignores it.
    """
    resolved_target_epc = target_epc or DEFAULT_TARGET_EPC

    predicted_uplift_pct = max(
        0.0,
        model_or_calibrated_delta(
            current_epc, resolved_target_epc, property_features
        ),
    )
    predicted_uplift_value = current_value * (predicted_uplift_pct / 100.0)
    post_retrofit_value = current_value + predicted_uplift_value

    indicative_range_low_pct = max(0.0, predicted_uplift_pct - RANGE_LOW_OFFSET_PCT)
    indicative_range_high_pct = predicted_uplift_pct + RANGE_HIGH_OFFSET_PCT
    indicative_range_low_value = current_value * (
        1.0 + indicative_range_low_pct / 100.0
    )
    indicative_range_high_value = current_value * (
        1.0 + indicative_range_high_pct / 100.0
    )

    return ValuationResult(
        current_value=current_value,
        post_retrofit_value=post_retrofit_value,
        predicted_uplift_value=predicted_uplift_value,
        predicted_uplift_pct=predicted_uplift_pct,
        indicative_range_low_value=indicative_range_low_value,
        indicative_range_high_value=indicative_range_high_value,
        indicative_range_low_pct=indicative_range_low_pct,
        indicative_range_high_pct=indicative_range_high_pct,
        disclaimer=DISCLAIMER,
    )
