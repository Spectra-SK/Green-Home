"""Deterministic Green Home Score calculation.

Implements the team's detailed s1-s7 mathematical specification:
    S = round(100 * sum(w_k * s_k) / sum(w_k for k available))
for the 7 fixed-weight components below, each s_k in [0, 100]. Any
component whose input data is absent is excluded from both the
weighted sum and the weight total (renormalization), and a
`low_coverage` flag is raised if less than 70% of the total weight was
available.

The LLM layer must never compute this itself - this module is the
single source of truth for score math so results are reproducible and
auditable.
"""

from enum import Enum

from pydantic import BaseModel, Field

# Fixed component weights (sum to 1.0) - DO NOT change without updating CLAUDE.md
WEIGHTS = {
    "epc_rating": 0.25,  # s1
    "energy_intensity": 0.20,  # s2
    "insulation": 0.15,  # s3
    "heating": 0.15,  # s4
    "glazing": 0.10,  # s5
    "renewable_energy": 0.10,  # s6
    "smart_controls": 0.05,  # s7
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

LOW_COVERAGE_THRESHOLD = 0.70


class EpcRating(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


_EPC_SCORES: dict[EpcRating, int] = {
    EpcRating.A: 100,
    EpcRating.B: 85,
    EpcRating.C: 70,
    EpcRating.D: 55,
    EpcRating.E: 40,
    EpcRating.F: 25,
    EpcRating.G: 10,
}


class ConditionLevel(str, Enum):
    """Condition of a single insulation location (loft/wall/floor)."""

    GOOD = "Good"
    MEDIUM = "Medium"
    POOR = "Poor"
    NONE = "None"  # no insulation present at that location


_CONDITION_SCORES: dict[ConditionLevel, int] = {
    ConditionLevel.GOOD: 100,
    ConditionLevel.MEDIUM: 65,
    ConditionLevel.POOR: 30,
    ConditionLevel.NONE: 0,
}


def insulation_level_to_condition(level: str) -> ConditionLevel:
    """Map a coarse dataset insulation level ('Good'/'Moderate'/'Poor')
    to the detailed ConditionLevel used for loft/wall/floor scoring."""
    if level == "Good":
        return ConditionLevel.GOOD
    if level == "Moderate":
        return ConditionLevel.MEDIUM
    return ConditionLevel.POOR


class HeatingTech(str, Enum):
    HEAT_PUMP = "Heat Pump"
    HYBRID = "Hybrid"
    DISTRICT = "District"
    CONDENSING_GAS = "Condensing Gas"
    STANDARD_GAS = "Standard Gas"
    STORAGE = "Storage"
    DIRECT_ELECTRIC = "Direct Electric"
    OIL_LPG = "Oil/LPG"


_HEATING_TECH_SCORES: dict[HeatingTech, int] = {
    HeatingTech.HEAT_PUMP: 100,
    HeatingTech.HYBRID: 85,
    HeatingTech.DISTRICT: 80,
    HeatingTech.CONDENSING_GAS: 70,
    HeatingTech.STANDARD_GAS: 55,
    HeatingTech.STORAGE: 45,
    HeatingTech.DIRECT_ELECTRIC: 40,
    HeatingTech.OIL_LPG: 35,
}

HEATING_AGE_CAP_YEARS = 25.0


def heating_type_to_tech(heating_type: str) -> HeatingTech:
    """Map a raw dataset heating_type (e.g. 'Heat Pump', 'Gas Boiler',
    'Oil Boiler', 'Electric Storage') to the detailed HeatingTech
    category used by the scoring formula."""
    if heating_type == "Heat Pump":
        return HeatingTech.HEAT_PUMP
    if heating_type == "Gas Boiler":
        return HeatingTech.STANDARD_GAS
    if heating_type == "Oil Boiler":
        return HeatingTech.OIL_LPG
    if heating_type == "Electric Storage":
        return HeatingTech.STORAGE
    return HeatingTech.DIRECT_ELECTRIC


class GlazingType(str, Enum):
    SINGLE = "Single"
    DOUBLE = "Double"
    TRIPLE = "Triple"


_GLAZING_TYPE_SCORES: dict[GlazingType, int] = {
    GlazingType.TRIPLE: 100,
    GlazingType.DOUBLE: 75,
    GlazingType.SINGLE: 20,
}


class SealCondition(str, Enum):
    GOOD = "Good"
    MEDIUM = "Medium"
    POOR = "Poor"


_SEAL_SCORES: dict[SealCondition, int] = {
    SealCondition.GOOD: 100,
    SealCondition.MEDIUM: 65,
    SealCondition.POOR: 25,
}


class EnergyIntensityInputs(BaseModel):
    elec_kwh: float = Field(ge=0)
    gas_kwh: float = Field(ge=0)
    other_kwh: float = Field(default=0.0, ge=0)
    floor_area_m2: float = Field(gt=0)


class InsulationInputs(BaseModel):
    loft: ConditionLevel
    wall: ConditionLevel
    floor: ConditionLevel


class HeatingInputs(BaseModel):
    tech: HeatingTech
    seasonal_efficiency_pct: float = Field(ge=0, le=100)
    age_years: float = Field(ge=0)


class GlazingInputs(BaseModel):
    glazing_type: GlazingType
    seal_condition: SealCondition


class RenewablesInputs(BaseModel):
    """Absent entirely (None at the ScoreInputs level) scores 0, same as
    an unmetered/solar-free home - renewables never trigger the
    missing-component renormalization path."""

    e_self_kwh: float = Field(ge=0)
    e_elec_demand_kwh: float = Field(ge=0)


class SmartControlsInputs(BaseModel):
    smart_thermostat: bool
    smart_meter: bool
    programmable: bool
    zoned: bool


class ScoreInputs(BaseModel):
    epc_rating: EpcRating | None = None
    energy: EnergyIntensityInputs | None = None
    insulation: InsulationInputs | None = None
    heating: HeatingInputs | None = None
    glazing: GlazingInputs | None = None
    renewables: RenewablesInputs | None = None
    smart_controls: SmartControlsInputs | None = None


class ComponentScores(BaseModel):
    epc_rating: float | None
    energy_intensity: float | None
    insulation: float | None
    heating: float | None
    glazing: float | None
    renewable_energy: float
    smart_controls: float | None


class GreenHomeScoreResult(BaseModel):
    score: int
    classification: str
    component_scores: ComponentScores
    weights: dict[str, float]
    coverage: float
    low_coverage: bool


def classify_score(score: int) -> str:
    if score >= 80:
        return "Highly efficient"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Moderate"
    if score >= 30:
        return "Poor"
    return "Very poor"


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _score_epc(epc_rating: EpcRating | None) -> float | None:
    if epc_rating is None:
        return None
    return float(_EPC_SCORES[epc_rating])


def _score_energy_intensity(energy: EnergyIntensityInputs | None) -> float | None:
    if energy is None:
        return None
    x = (energy.elec_kwh + energy.gas_kwh + energy.other_kwh) / energy.floor_area_m2
    return _clamp(100.0 * (250.0 - x) / (250.0 - 50.0))


def _score_insulation(insulation: InsulationInputs | None) -> float | None:
    if insulation is None:
        return None
    return (
        0.40 * _CONDITION_SCORES[insulation.loft]
        + 0.40 * _CONDITION_SCORES[insulation.wall]
        + 0.20 * _CONDITION_SCORES[insulation.floor]
    )


def _score_heating(heating: HeatingInputs | None) -> float | None:
    if heating is None:
        return None
    tech_score = _HEATING_TECH_SCORES[heating.tech]
    efficiency_score = _clamp(heating.seasonal_efficiency_pct)
    age_score = _clamp(
        100.0 * (1.0 - min(heating.age_years, HEATING_AGE_CAP_YEARS) / HEATING_AGE_CAP_YEARS)
    )
    return 0.40 * tech_score + 0.40 * efficiency_score + 0.20 * age_score


def _score_glazing(glazing: GlazingInputs | None) -> float | None:
    if glazing is None:
        return None
    type_score = _GLAZING_TYPE_SCORES[glazing.glazing_type]
    seal_score = _SEAL_SCORES[glazing.seal_condition]
    return 0.70 * type_score + 0.30 * seal_score


def _score_renewables(renewables: RenewablesInputs | None) -> float:
    if renewables is None or renewables.e_elec_demand_kwh <= 0:
        return 0.0
    return _clamp(100.0 * renewables.e_self_kwh / renewables.e_elec_demand_kwh)


def _score_smart_controls(smart: SmartControlsInputs | None) -> float | None:
    if smart is None:
        return None
    return (
        0.30 * (100.0 if smart.smart_thermostat else 0.0)
        + 0.15 * (100.0 if smart.smart_meter else 0.0)
        + 0.30 * (100.0 if smart.programmable else 0.0)
        + 0.25 * (100.0 if smart.zoned else 0.0)
    )


# The app, evaluate.py, and battle.py all only collect one coarse value
# per category (a single insulation level, a single glazing type, a
# single smart_controls flag). Where the detailed s1-s7 spec wants a
# finer breakdown we don't collect (seal condition, seasonal heating
# efficiency, system age, per-device smart controls), every caller fills
# in the same documented default assumptions below rather than guessing
# independently per call site.
DEFAULT_SEAL_CONDITION = SealCondition.MEDIUM
DEFAULT_HEATING_SEASONAL_EFFICIENCY_PCT = 75.0
DEFAULT_HEATING_AGE_YEARS = 10.0
DEFAULT_SOLAR_SELF_CONSUMPTION_CAP_KWH = 2500.0


def build_score_inputs(
    epc_rating: EpcRating,
    insulation_level: str,
    heating_type: str,
    glazing_type: GlazingType,
    solar: bool,
    smart_controls: bool,
    elec_kwh: float,
    gas_kwh: float,
    floor_area_m2: float,
) -> ScoreInputs:
    """Build full ScoreInputs from the coarse flat fields collected across
    the app/dataset/battle engine, applying the default assumptions
    documented above for sub-fields that data doesn't track."""
    insulation_condition = insulation_level_to_condition(insulation_level)
    self_consumption = (
        min(DEFAULT_SOLAR_SELF_CONSUMPTION_CAP_KWH, elec_kwh) if solar else 0.0
    )
    return ScoreInputs(
        epc_rating=epc_rating,
        energy=EnergyIntensityInputs(
            elec_kwh=elec_kwh, gas_kwh=gas_kwh, floor_area_m2=floor_area_m2
        ),
        insulation=InsulationInputs(
            loft=insulation_condition,
            wall=insulation_condition,
            floor=insulation_condition,
        ),
        heating=HeatingInputs(
            tech=heating_type_to_tech(heating_type),
            seasonal_efficiency_pct=DEFAULT_HEATING_SEASONAL_EFFICIENCY_PCT,
            age_years=DEFAULT_HEATING_AGE_YEARS,
        ),
        glazing=GlazingInputs(
            glazing_type=glazing_type, seal_condition=DEFAULT_SEAL_CONDITION
        ),
        renewables=RenewablesInputs(
            e_self_kwh=self_consumption, e_elec_demand_kwh=elec_kwh
        ),
        smart_controls=SmartControlsInputs(
            smart_thermostat=smart_controls,
            smart_meter=smart_controls,
            programmable=smart_controls,
            zoned=smart_controls,
        ),
    )


def _round1(val: float | None) -> float | None:
    """Round a subscore to at most 1 decimal place, leaving a missing
    (None) component as-is."""
    return val if val is None else round(float(val), 1)


def compute_component_scores(inputs: ScoreInputs) -> ComponentScores:
    return ComponentScores(
        epc_rating=_round1(_score_epc(inputs.epc_rating)),
        energy_intensity=_round1(_score_energy_intensity(inputs.energy)),
        insulation=_round1(_score_insulation(inputs.insulation)),
        heating=_round1(_score_heating(inputs.heating)),
        glazing=_round1(_score_glazing(inputs.glazing)),
        renewable_energy=_round1(_score_renewables(inputs.renewables)),
        smart_controls=_round1(_score_smart_controls(inputs.smart_controls)),
    )


def compute_green_home_score(inputs: ScoreInputs) -> GreenHomeScoreResult:
    components = compute_component_scores(inputs)
    component_values = components.model_dump()

    weighted_sum = 0.0
    available_weight = 0.0
    for key, weight in WEIGHTS.items():
        value = component_values[key]
        if value is None:
            continue
        weighted_sum += weight * value
        available_weight += weight

    if available_weight <= 0:
        raise ValueError("No scoreable components were provided.")

    normalized_score = weighted_sum / available_weight
    # Mathematically this weighted average of 0-100-bounded components
    # already can't leave [0, 100], but clamp explicitly anyway - a
    # single source of truth guaranteeing the final score, not just
    # each component, never overflows or underflows. round() with no
    # ndigits already returns int, so the final score is always a
    # whole number.
    score = max(0, min(100, round(normalized_score)))

    return GreenHomeScoreResult(
        score=score,
        classification=classify_score(score),
        component_scores=components,
        weights=WEIGHTS,
        coverage=available_weight,
        low_coverage=available_weight < LOW_COVERAGE_THRESHOLD,
    )
