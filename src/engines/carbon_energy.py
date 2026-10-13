"""Deterministic energy and carbon-saving calculations for retrofit packages.

Implements the Part II non-linear heat-demand reduction model: fabric
measures (loft/wall/floor insulation, glazing, draught seals) each
avoid a fixed share of useful heat demand (Table 1); a heat pump then
draws its electricity from whatever heat demand remains via its SCOP;
solar generates a fixed yield per kWp, a fraction of which is
self-consumed depending on whether it's paired with a battery.

All numbers here are computed from fixed physical rules - the LLM layer
only narrates this output, it never computes energy or carbon figures
itself.
"""

from collections.abc import Mapping

from pydantic import BaseModel

from src.engines.scoring import ConditionLevel, GlazingType, SealCondition

HEAT_PUMP_SCOP = 3.5

# Smart controls' behavioral savings aren't separately quantified in
# the official DEFRA-aligned reference carbon figures (P1-P5 benchmarks
# in tests/test_engines.py are identical with/without them) - kept as a
# named constant, set to 0, so the lever stays documented rather than
# silently deleted.
SMART_CONTROLS_ELEC_REDUCTION = 0.0

CONDENSING_BOILER_EFFICIENCY_PCT = 92.0

# Default assumptions when property_features doesn't specify these -
# see calculate_energy_and_carbon's docstring for the recognized keys.
DEFAULT_BOILER_EFFICIENCY_PCT = 70.0
DEFAULT_SEAL_CONDITION = SealCondition.MEDIUM
DEFAULT_SOLAR_KWP = 4.0

# UK DEFRA/DESNZ greenhouse gas reporting conversion factors (Equation 14).
ELEC_CARBON_FACTOR_KG_PER_KWH = 0.20705
GAS_CARBON_FACTOR_KG_PER_KWH = 0.18254

# Table 1: avoided heat-demand share (% of useful heat demand) for each
# fabric condition/type. "None"/"Single"/"Poor" (seals) are the
# no-measure baseline, worth 0%.
LOFT_AVOIDED_SHARE_PCT: dict[ConditionLevel, float] = {
    ConditionLevel.NONE: 0.0,
    ConditionLevel.POOR: 4.0,
    ConditionLevel.MEDIUM: 8.0,
    ConditionLevel.GOOD: 12.0,
}
WALL_AVOIDED_SHARE_PCT: dict[ConditionLevel, float] = {
    ConditionLevel.NONE: 0.0,
    ConditionLevel.POOR: 8.0,
    ConditionLevel.MEDIUM: 16.0,
    ConditionLevel.GOOD: 25.0,
}
FLOOR_AVOIDED_SHARE_PCT: dict[ConditionLevel, float] = {
    ConditionLevel.NONE: 0.0,
    ConditionLevel.POOR: 2.0,
    ConditionLevel.MEDIUM: 4.0,
    ConditionLevel.GOOD: 6.0,
}
GLAZING_AVOIDED_SHARE_PCT: dict[GlazingType, float] = {
    GlazingType.SINGLE: 0.0,
    GlazingType.DOUBLE: 10.0,
    GlazingType.TRIPLE: 14.0,
}
SEAL_AVOIDED_SHARE_PCT: dict[SealCondition, float] = {
    SealCondition.POOR: 0.0,
    SealCondition.MEDIUM: 2.0,
    SealCondition.GOOD: 4.0,
}

_GLAZING_UPGRADE = {
    GlazingType.SINGLE: GlazingType.DOUBLE,
    GlazingType.DOUBLE: GlazingType.TRIPLE,
    GlazingType.TRIPLE: GlazingType.TRIPLE,
}

# Per-kWp generation rate itself stays uncapped (a bigger array simply
# generates more); the research-specified 2,500 kWh/yr cap is instead
# applied to the self-consumed/grid-offsetting portion below, via
# SOLAR_SELF_CONSUMPTION_CAP_KWH.
SOLAR_KWH_PER_KWP = 850.0
SOLAR_SELF_CONSUMPTION_NO_BATTERY = 0.35
SOLAR_SELF_CONSUMPTION_WITH_BATTERY = 0.65

# The self-consumed (grid-offsetting) portion of solar generation is
# capped at this annual figure regardless of array size or battery
# presence - a larger installation can still generate more than this,
# but only ever offsets up to 2,500 kWh/yr of grid import. At
# DEFAULT_SOLAR_KWP (4kWp) this never binds (2,210/1,190 kWh with/without
# a battery), so the Lloyds-reference P1-P5 benchmarks are unaffected;
# it only takes effect for a larger-than-default solar_kwp.
SOLAR_SELF_CONSUMPTION_CAP_KWH = 2500.0


class EnergyCarbonResult(BaseModel):
    baseline_elec: float
    post_elec: float
    elec_diff: float
    baseline_gas: float
    post_gas: float
    gas_diff: float
    net_kwh_saving: float
    carbon_reduction_kg: float
    # Electricity and gas carbon impact reported separately (Equation 14),
    # in tonnes CO2e. elec_diff_tonnes is negative when electricity use
    # rises (e.g. a heat pump's draw exceeding any solar offset).
    elec_diff_tonnes: float
    gas_diff_tonnes: float
    carbon_reduction_tonnes: float


def avoided_heat_share_fraction(
    loft: ConditionLevel,
    wall: ConditionLevel,
    floor: ConditionLevel,
    glazing: GlazingType,
    seal: SealCondition,
) -> float:
    """R: the fraction (0-1) of useful heat demand avoided by this
    fabric state, per Table 1."""
    pct = (
        LOFT_AVOIDED_SHARE_PCT[loft]
        + WALL_AVOIDED_SHARE_PCT[wall]
        + FLOOR_AVOIDED_SHARE_PCT[floor]
        + GLAZING_AVOIDED_SHARE_PCT[glazing]
        + SEAL_AVOIDED_SHARE_PCT[seal]
    )
    return pct / 100.0


def calculate_energy_and_carbon(
    baseline_elec: float,
    baseline_gas: float,
    retrofits_applied: list[str],
    property_features: Mapping[str, object],
) -> EnergyCarbonResult:
    """Apply a retrofit package to baseline consumption.

    `retrofits_applied` is a subset of {"insulation", "heat_pump",
    "solar_pv", "solar_pv_battery", "glazing", "seals",
    "condensing_boiler", "smart_controls"} - the same keys produced by
    `RetrofitRecommendation.key` in retrofits.py (plus the solar/boiler
    variants retrofits.py doesn't offer).

    `property_features` carries the *current* (pre-retrofit) fabric
    state, read with these optional keys:
    - "heating": current heating type string (e.g. "Heat Pump")
    - "insulation": current ConditionLevel applied to loft/wall/floor
      alike (defaults to ConditionLevel.POOR); "insulation_loft",
      "insulation_wall", "insulation_floor" each override it individually
      when the three locations differ
    - "glazing": current GlazingType (defaults to GlazingType.SINGLE)
    - "seal_condition": current SealCondition (defaults to
      DEFAULT_SEAL_CONDITION)
    - "boiler_efficiency_pct": current gas boiler seasonal efficiency,
      0-100 (defaults to DEFAULT_BOILER_EFFICIENCY_PCT)
    - "solar_kwp": capacity of solar being installed, if "solar_pv" or
      "solar_pv_battery" is in retrofits_applied (defaults to
      DEFAULT_SOLAR_KWP)

    Physics:
    - Useful heat demand today: Q0 = baseline_gas * eta_0.
    - Fabric measures each avoid a fixed share of useful heat demand
      (Table 1); R_old/R_new are the current/post-retrofit avoided
      shares. Q_new = Q0 * (1 - R_new) / (1 - R_old).
    - If a heat pump is installed, gas drops to 0 and electricity rises
      by Q_new / HEAT_PUMP_SCOP.
    - Otherwise Q_new converts back to gas input via the same boiler
      efficiency (a boiler-efficiency upgrade isn't modeled here).
    - Solar generates solar_kwp * SOLAR_KWH_PER_KWP kWh/yr, of which a
      fixed fraction is self-consumed (more with a battery); that
      self-consumed amount offsets grid electricity import only.
    """
    currently_heat_pump = property_features.get("heating") == "Heat Pump"
    installing_heat_pump = "heat_pump" in retrofits_applied and not currently_heat_pump

    default_insulation = property_features.get("insulation", ConditionLevel.POOR)
    old_loft = property_features.get("insulation_loft", default_insulation)
    old_wall = property_features.get("insulation_wall", default_insulation)
    old_floor = property_features.get("insulation_floor", default_insulation)
    old_glazing = property_features.get("glazing", GlazingType.SINGLE)
    seal = property_features.get("seal_condition", DEFAULT_SEAL_CONDITION)
    eta_0 = property_features.get("boiler_efficiency_pct", DEFAULT_BOILER_EFFICIENCY_PCT) / 100.0

    insulation_retrofit = "insulation" in retrofits_applied
    new_loft = ConditionLevel.GOOD if insulation_retrofit else old_loft
    new_wall = ConditionLevel.GOOD if insulation_retrofit else old_wall
    new_floor = ConditionLevel.GOOD if insulation_retrofit else old_floor
    new_glazing = (
        _GLAZING_UPGRADE[old_glazing] if "glazing" in retrofits_applied else old_glazing
    )
    # Draught-proofing (R4) reaches a "Medium" seal, not "Good" - full
    # draught/ventilation sealing is a separate, more extensive measure
    # this catalog doesn't offer.
    new_seal = SealCondition.MEDIUM if "seals" in retrofits_applied else seal

    r_old = avoided_heat_share_fraction(old_loft, old_wall, old_floor, old_glazing, seal)
    r_new = avoided_heat_share_fraction(new_loft, new_wall, new_floor, new_glazing, new_seal)
    fabric_factor = (1.0 - r_new) / (1.0 - r_old) if r_old < 1.0 else 0.0

    if installing_heat_pump:
        # Fuel decoupling: remaining useful heat demand moves entirely
        # to electricity via the heat pump's SCOP.
        q0 = baseline_gas * eta_0
        q_new = q0 * fabric_factor
        post_gas = 0.0
        elec_after_heating = baseline_elec + q_new / HEAT_PUMP_SCOP
    elif currently_heat_pump:
        # Heating is already electric; fabric upgrades reduce the heat
        # pump's own electricity draw. Approximated as the same fabric
        # factor applied to total baseline electricity (no gas/baseload
        # split available for an already-electric home).
        post_gas = baseline_gas
        elec_after_heating = baseline_elec * fabric_factor
    else:
        # Heating stays on gas: useful heat demand drops, then converts
        # back to gas input. A condensing-boiler upgrade raises that
        # conversion efficiency; Q0 itself still uses the home's current
        # (pre-upgrade) efficiency, since Q0 is today's useful heat demand.
        q0 = baseline_gas * eta_0
        q_new = q0 * fabric_factor
        new_eta = (
            CONDENSING_BOILER_EFFICIENCY_PCT / 100.0
            if "condensing_boiler" in retrofits_applied
            else eta_0
        )
        post_gas = q_new / new_eta if new_eta > 0 else 0.0
        elec_after_heating = baseline_elec

    if "smart_controls" in retrofits_applied:
        elec_after_heating *= 1.0 - SMART_CONTROLS_ELEC_REDUCTION

    solar_lever = next(
        (lever for lever in ("solar_pv_battery", "solar_pv") if lever in retrofits_applied),
        None,
    )
    if solar_lever is not None:
        solar_kwp = property_features.get("solar_kwp", DEFAULT_SOLAR_KWP)
        generation = solar_kwp * SOLAR_KWH_PER_KWP
        self_consumption_rate = (
            SOLAR_SELF_CONSUMPTION_WITH_BATTERY
            if solar_lever == "solar_pv_battery"
            else SOLAR_SELF_CONSUMPTION_NO_BATTERY
        )
        self_consumed = min(SOLAR_SELF_CONSUMPTION_CAP_KWH, generation * self_consumption_rate)
        solar_offset = min(self_consumed, elec_after_heating)
        post_elec = max(0.0, elec_after_heating - solar_offset)
    else:
        post_elec = elec_after_heating

    elec_diff = baseline_elec - post_elec
    gas_diff = baseline_gas - post_gas
    net_kwh_saving = elec_diff + gas_diff

    # Equation 14: delta_carbon_tonnes = ((baseline_elec - post_elec) * EF_elec
    # + (baseline_gas - post_gas) * EF_gas) / 1000.0, reported for each fuel
    # separately as well as combined.
    elec_diff_tonnes = elec_diff * ELEC_CARBON_FACTOR_KG_PER_KWH / 1000.0
    gas_diff_tonnes = gas_diff * GAS_CARBON_FACTOR_KG_PER_KWH / 1000.0
    carbon_reduction_tonnes = elec_diff_tonnes + gas_diff_tonnes
    carbon_reduction_kg = carbon_reduction_tonnes * 1000.0

    return EnergyCarbonResult(
        baseline_elec=baseline_elec,
        post_elec=post_elec,
        elec_diff=elec_diff,
        baseline_gas=baseline_gas,
        post_gas=post_gas,
        gas_diff=gas_diff,
        net_kwh_saving=net_kwh_saving,
        carbon_reduction_kg=carbon_reduction_kg,
        elec_diff_tonnes=elec_diff_tonnes,
        gas_diff_tonnes=gas_diff_tonnes,
        carbon_reduction_tonnes=carbon_reduction_tonnes,
    )
