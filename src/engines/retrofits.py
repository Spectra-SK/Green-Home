"""Deterministic retrofit recommendation engine.

Given a property's current features, produces a prioritized list of
feasible green retrofits. All suitability/priority/impact values are
computed from fixed rules here - the LLM layer only narrates this
output, it never decides feasibility or sequencing itself.
"""

from collections.abc import Iterable
from enum import Enum
from typing import Literal

from pydantic import BaseModel

HEAT_PUMP_SCOP = 3.5  # Part II revision (was COP 3.2)
SOLAR_DEFAULT_KWP = 4.0
SOLAR_KWH_PER_KWP = 850.0
SOLAR_SELF_CONSUMPTION_NO_BATTERY_PCT = 35.0
INSULATION_HEATING_REDUCTION_PCT = 15.0


class Suitability(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class PropertyFeatures(BaseModel):
    insulation: Literal["Poor", "Moderate", "Good"]
    heating: str
    glazing: Literal["Single", "Double", "Triple"]
    solar: bool
    smart_controls: bool


_GLAZING_UPGRADE = {"Single": "Double", "Double": "Triple", "Triple": "Triple"}


def apply_retrofits(
    insulation: str,
    heating_type: str,
    glazing: str,
    solar: bool,
    smart_controls: bool,
    retrofit_keys: Iterable[str],
) -> tuple[str, str, str, bool, bool]:
    """Apply a set of retrofit keys (the same vocabulary as
    RetrofitRecommendation.key / carbon_energy's retrofits_applied -
    'insulation', 'heat_pump', 'glazing', 'solar_pv', 'smart_controls')
    to a property's coarse feature set, returning the resulting
    (insulation, heating_type, glazing, solar, smart_controls).

    Glazing moves exactly one tier (Single -> Double -> Triple); EPC
    rating itself is never changed here since re-certifying it isn't
    modeled - callers recompute the Green Home Score with the same EPC
    band but these updated physical features."""
    keys = set(retrofit_keys)
    new_insulation = "Good" if "insulation" in keys else insulation
    new_heating_type = "Heat Pump" if "heat_pump" in keys else heating_type
    new_glazing = _GLAZING_UPGRADE.get(glazing, glazing) if "glazing" in keys else glazing
    new_solar = solar or ("solar_pv" in keys)
    new_smart_controls = smart_controls or ("smart_controls" in keys)
    return new_insulation, new_heating_type, new_glazing, new_solar, new_smart_controls


class RetrofitRecommendation(BaseModel):
    key: str
    name: str
    suitability: Suitability
    priority: int | Literal["Contingent"]
    estimated_impact: str
    reason: str


class RetrofitRecommender:
    """Evaluates a fixed catalogue of retrofits against a property's features."""

    def recommend(self, features: PropertyFeatures) -> list[RetrofitRecommendation]:
        recommendations: list[RetrofitRecommendation] = []

        insulation_rec = self._evaluate_insulation(features)
        if insulation_rec:
            recommendations.append(insulation_rec)

        heat_pump_rec = self._evaluate_heat_pump(features)
        if heat_pump_rec:
            recommendations.append(heat_pump_rec)

        glazing_rec = self._evaluate_glazing(features)
        if glazing_rec:
            recommendations.append(glazing_rec)

        solar_rec = self._evaluate_solar(features)
        if solar_rec:
            recommendations.append(solar_rec)

        smart_controls_rec = self._evaluate_smart_controls(features)
        if smart_controls_rec:
            recommendations.append(smart_controls_rec)

        return sorted(recommendations, key=self._sort_key)

    @staticmethod
    def _sort_key(rec: RetrofitRecommendation) -> tuple[int, int]:
        # Contingent items cannot proceed yet, so they sort after every
        # actionable (numeric-priority) recommendation.
        if rec.priority == "Contingent":
            return (1, 0)
        return (0, rec.priority)

    @staticmethod
    def _evaluate_insulation(
        features: PropertyFeatures,
    ) -> RetrofitRecommendation | None:
        if features.insulation == "Good":
            return None
        return RetrofitRecommendation(
            key="insulation",
            name="Roof/loft insulation upgrade",
            suitability=Suitability.HIGH,
            priority=1,
            estimated_impact=f"-{INSULATION_HEATING_REDUCTION_PCT:.0f}% space heating demand",
            reason=(
                f"Current insulation is '{features.insulation}'. Upgrading it "
                "cuts space heating demand and must happen before a heat pump "
                "is sized, since it lowers the heat load the pump needs to cover."
            ),
        )

    @staticmethod
    def _evaluate_heat_pump(
        features: PropertyFeatures,
    ) -> RetrofitRecommendation | None:
        if features.heating == "Heat Pump":
            return None

        if features.insulation == "Poor":
            return RetrofitRecommendation(
                key="heat_pump",
                name="Air/ground source heat pump",
                suitability=Suitability.MEDIUM,
                priority="Contingent",
                estimated_impact=(
                    f"Eliminates gas use; adds electricity at SCOP {HEAT_PUMP_SCOP}"
                ),
                reason=(
                    "Insulation is 'Poor', so a heat pump would be oversized and "
                    "inefficient. Insulation must be upgraded first; this "
                    "recommendation becomes actionable once that is done."
                ),
            )

        suitability = (
            Suitability.HIGH if features.insulation == "Good" else Suitability.MEDIUM
        )
        return RetrofitRecommendation(
            key="heat_pump",
            name="Air/ground source heat pump",
            suitability=suitability,
            priority=2,
            estimated_impact=(
                f"Eliminates gas use; adds electricity at SCOP {HEAT_PUMP_SCOP}"
            ),
            reason=(
                f"Current heating is '{features.heating}'. Insulation is "
                f"'{features.insulation}', so the home is ready for a heat pump "
                "without oversizing it."
            ),
        )

    @staticmethod
    def _evaluate_glazing(
        features: PropertyFeatures,
    ) -> RetrofitRecommendation | None:
        if features.glazing not in ("Single", "Double"):
            return None
        suitability = (
            Suitability.HIGH if features.glazing == "Single" else Suitability.MEDIUM
        )
        upgrade_to = "double" if features.glazing == "Single" else "triple"
        return RetrofitRecommendation(
            key="glazing",
            name=f"Upgrade to {upgrade_to} glazing",
            suitability=suitability,
            priority=3,
            estimated_impact="Reduces fabric heat loss and draughts",
            reason=f"Current glazing is '{features.glazing}'.",
        )

    @staticmethod
    def _evaluate_solar(
        features: PropertyFeatures,
    ) -> RetrofitRecommendation | None:
        if features.solar:
            return None
        return RetrofitRecommendation(
            key="solar_pv",
            name="Solar PV installation",
            suitability=Suitability.MEDIUM,
            priority=4,
            estimated_impact=(
                f"Up to {SOLAR_DEFAULT_KWP * SOLAR_KWH_PER_KWP * SOLAR_SELF_CONSUMPTION_NO_BATTERY_PCT / 100:.0f} "
                f"kWh/yr grid offset ({SOLAR_DEFAULT_KWP:.0f}kWp, no battery)"
            ),
            reason="No solar PV currently installed.",
        )

    @staticmethod
    def _evaluate_smart_controls(
        features: PropertyFeatures,
    ) -> RetrofitRecommendation | None:
        if features.smart_controls:
            return None
        return RetrofitRecommendation(
            key="smart_controls",
            name="Smart energy management controls",
            suitability=Suitability.LOW,
            priority=5,
            estimated_impact="Small behavioral/scheduling energy savings",
            reason="No smart energy management controls currently installed.",
        )
