"""Retrofit Battle & Package Recommendation Engine.

Codifies the 13 Lloyds standard retrofit interventions (R1-R13) and the
5 fabric-first sequencing packages (P1-P5) built from them. Every
package that includes the heat pump (R8) also bundles the core fabric
measures (R1 loft, R2 wall, R3 floor insulation) - fabric is installed
before electrification, by construction of the package definitions
themselves, never by a runtime sequencing check.
"""

from pydantic import BaseModel

from src.engines.carbon_energy import EnergyCarbonResult, calculate_energy_and_carbon
from src.engines.retrofits import apply_retrofits
from src.engines.scoring import (
    EpcRating,
    GlazingType,
    build_score_inputs,
    compute_green_home_score,
    insulation_level_to_condition,
)

# Standardised indicative costs (GBP) and EPC-point uplift, calibrated
# for UK residential retrofits.
RETROFIT_CATALOG: dict[str, dict] = {
    "R1": {"name": "Loft insulation (>=270mm)", "cost": 1200, "key": "loft_insulation", "epc_uplift": 3},
    "R2": {"name": "Wall insulation (cavity/solid)", "cost": 2800, "key": "cavity_wall_insulation", "epc_uplift": 10},
    "R3": {"name": "Floor insulation", "cost": 1800, "key": "floor_insulation", "epc_uplift": 2},
    "R4": {"name": "Draught-proofing & seals", "cost": 450, "key": "draught_proofing", "epc_uplift": 2},
    "R5": {"name": "Double glazing (A-rated)", "cost": 4500, "key": "double_glazing", "epc_uplift": 5},
    "R6": {"name": "Triple glazing", "cost": 6500, "key": "triple_glazing", "epc_uplift": 6},
    "R7": {"name": "Condensing gas boiler (92%)", "cost": 2600, "key": "condensing_boiler", "epc_uplift": 9},
    "R8": {"name": "Air-source heat pump (SCOP 3.2-3.5)", "cost": 9500, "key": "heat_pump", "epc_uplift": 14},
    "R9": {"name": "Solar PV 4 kWp (standalone)", "cost": 5500, "key": "solar_pv", "epc_uplift": 7},
    "R10": {"name": "Solar PV 4 kWp + Battery", "cost": 8500, "key": "solar_battery", "epc_uplift": 8},
    "R11": {"name": "Smart thermostat", "cost": 250, "key": "smart_thermostat", "epc_uplift": 2},
    "R12": {"name": "Smart meter installation", "cost": 50, "key": "smart_meter", "epc_uplift": 0},
    "R13": {"name": "Zoned TRVs & controls", "cost": 600, "key": "zoned_controls", "epc_uplift": 2},
}

# Ordered cheapest/least-ambitious to most expensive/most-ambitious -
# P1's cost is a strict lower bound on P2-P5's, matching the "Quick
# Wins" -> "Whole-Home Net-Zero" progression below.
PACKAGE_ORDER = ["P1", "P2", "P3", "P4", "P5"]

PACKAGES: dict[str, dict] = {
    "P1": {
        "title": "Fabric First (Quick Wins)",
        "r_ids": ["R1", "R2", "R3", "R4", "R5"],
        "description": "Insulation, draught-proofing, and glazing only. Minimises thermal loss before heating replacement.",
    },
    "P2": {
        "title": "Fabric First + Modern Condensing Boiler",
        "r_ids": ["R1", "R2", "R3", "R4", "R5", "R7"],
        "description": "High fabric efficiency paired with modern 92% seasonal gas efficiency.",
    },
    "P3": {
        "title": "Clean Electrification (Fabric + Heat Pump)",
        "r_ids": ["R1", "R2", "R3", "R4", "R5", "R8"],
        "description": "Eliminates gas consumption. Requires fabric insulation first to prevent sizing failure.",
    },
    "P4": {
        "title": "Deep Decarbonisation (Fabric + HP + Solar/Battery)",
        "r_ids": ["R1", "R2", "R3", "R4", "R5", "R8", "R10"],
        "description": "Full electrification with 65% on-site solar battery self-consumption.",
    },
    "P5": {
        "title": "Whole-Home Net-Zero Package",
        "r_ids": ["R1", "R2", "R3", "R4", "R5", "R8", "R10", "R11", "R12", "R13"],
        "description": "Complete building envelope, renewable storage, and smart micro-zoned management.",
    },
}

# Maps each R-id's physical intervention to the carbon_energy.py lever
# vocabulary, for live per-property carbon estimation (see
# estimate_package_energy_and_carbon below). R12 (smart meter alone) has
# no direct energy-model lever.
R_ID_TO_LEVER: dict[str, str | None] = {
    "R1": "insulation",
    "R2": "insulation",
    "R3": "insulation",
    "R4": "seals",
    "R5": "glazing",
    "R6": "glazing",
    "R7": "condensing_boiler",
    "R8": "heat_pump",
    "R9": "solar_pv",
    "R10": "solar_pv_battery",
    "R11": "smart_controls",
    "R12": None,
    "R13": "smart_controls",
}

# R-ids that make up the "fabric" work a heat pump package must include
# before electrification (fabric-first sequencing).
FABRIC_R_IDS = ("R1", "R2", "R3")
HEAT_PUMP_R_ID = "R8"

VALID_OBJECTIVES = ("carbon", "energy", "score")


class RetrofitPlan(BaseModel):
    plan_id: str
    title: str
    description: str
    included_measures: list[str]
    total_estimated_cost: float
    projected_epc_uplift: int


def _compute_plan(plan_id: str) -> RetrofitPlan:
    meta = PACKAGES[plan_id]
    r_ids = meta["r_ids"]
    return RetrofitPlan(
        plan_id=plan_id,
        title=meta["title"],
        description=meta["description"],
        included_measures=[RETROFIT_CATALOG[rid]["name"] for rid in r_ids],
        total_estimated_cost=sum(RETROFIT_CATALOG[rid]["cost"] for rid in r_ids),
        projected_epc_uplift=sum(RETROFIT_CATALOG[rid]["epc_uplift"] for rid in r_ids),
    )


def estimate_package_energy_and_carbon(
    plan_id: str,
    baseline_elec: float,
    baseline_gas: float,
    property_features: dict,
) -> EnergyCarbonResult:
    """Live per-property energy/carbon estimate for one P1-P5 package,
    via carbon_energy.py's physics (see its docstring for the
    recognized `property_features` keys). Against the Lloyds reference
    baseline (18,000 kWh gas, 4,500 kWh elec; Poor loft/wall, no floor
    insulation; Single glazing; Poor seals; a 70%-efficient boiler),
    this reproduces the official P1-P5 annual carbon-saved figures in
    tests/test_engines.py."""
    r_ids = PACKAGES[plan_id]["r_ids"]
    levers = sorted({R_ID_TO_LEVER[r_id] for r_id in r_ids if R_ID_TO_LEVER[r_id]})
    return calculate_energy_and_carbon(
        baseline_elec=baseline_elec,
        baseline_gas=baseline_gas,
        retrofits_applied=levers,
        property_features=property_features,
    )


def estimate_package_score_uplift(
    plan_id: str,
    epc_rating: EpcRating | str,
    insulation_level: str,
    heating_type: str,
    glazing_type: GlazingType | str,
    solar: bool,
    smart_controls: bool,
    baseline_elec: float,
    baseline_gas: float,
    floor_area_m2: float,
) -> dict:
    """Live Green Home Score before/after one P1-P5 package, for this
    specific property - never a fixed/default baseline score. Uses the
    same engines /api/assessment and /api/what-if use (build_score_inputs
    + apply_retrofits + compute_green_home_score), driven by the
    package's own post-retrofit energy figures from
    estimate_package_energy_and_carbon."""
    epc_rating = EpcRating(epc_rating)
    glazing_type = GlazingType(glazing_type)

    before_score = compute_green_home_score(
        build_score_inputs(
            epc_rating=epc_rating,
            insulation_level=insulation_level,
            heating_type=heating_type,
            glazing_type=glazing_type,
            solar=solar,
            smart_controls=smart_controls,
            elec_kwh=baseline_elec,
            gas_kwh=baseline_gas,
            floor_area_m2=floor_area_m2,
        )
    )

    insulation_condition = insulation_level_to_condition(insulation_level)
    energy = estimate_package_energy_and_carbon(
        plan_id,
        baseline_elec,
        baseline_gas,
        property_features={
            "heating": heating_type,
            "insulation_loft": insulation_condition,
            "insulation_wall": insulation_condition,
            "insulation_floor": insulation_condition,
            "glazing": glazing_type,
        },
    )

    r_ids = PACKAGES[plan_id]["r_ids"]
    levers = sorted({R_ID_TO_LEVER[r_id] for r_id in r_ids if R_ID_TO_LEVER[r_id]})
    new_insulation, new_heating_type, new_glazing, new_solar, new_smart_controls = (
        apply_retrofits(
            insulation_level, heating_type, glazing_type, solar, smart_controls, levers
        )
    )

    after_score = compute_green_home_score(
        build_score_inputs(
            epc_rating=epc_rating,
            insulation_level=new_insulation,
            heating_type=new_heating_type,
            glazing_type=GlazingType(new_glazing),
            solar=new_solar,
            smart_controls=new_smart_controls,
            elec_kwh=energy.post_elec,
            gas_kwh=energy.post_gas,
            floor_area_m2=floor_area_m2,
        )
    )

    return {
        "before_score": before_score.score,
        "after_score": after_score.score,
        "score_uplift": after_score.score - before_score.score,
    }


def get_battle_plans(budget: float | None = None, objective: str = "carbon") -> dict:
    """Compares Plan A (Quick Wins / Fabric First, P1) against Plan B
    (Deep Decarbonisation / High Impact): the most affordable package
    that fits `budget`, versus the highest-EPC-uplift package that still
    fits `budget`, excluding Plan A itself.

    `objective` is accepted for forward compatibility with a future
    live, per-property physics comparison (carbon/energy/score), but
    today's comparison is catalog-level only (cost and EPC uplift), so
    changing it does not yet change which package is picked as Plan B.
    """
    if objective not in VALID_OBJECTIVES:
        raise ValueError(
            f"Unknown objective '{objective}'; expected one of {VALID_OBJECTIVES}."
        )

    plans = {plan_id: _compute_plan(plan_id) for plan_id in PACKAGE_ORDER}
    feasible_ids = [
        plan_id
        for plan_id in PACKAGE_ORDER
        if budget is None or plans[plan_id].total_estimated_cost <= budget
    ]

    if not feasible_ids:
        return {
            "plans": {},
            "budget": budget,
            "objective": objective,
            "notice": (
                "No package fits within the given budget - even "
                f"'{PACKAGES['P1']['title']}' "
                f"(£{plans['P1'].total_estimated_cost:,.0f}) exceeds it."
            ),
        }

    plan_a = plans[feasible_ids[0]]

    high_impact_candidates = [pid for pid in feasible_ids if pid != plan_a.plan_id]
    if high_impact_candidates:
        plan_b_id = max(
            high_impact_candidates,
            key=lambda pid: (plans[pid].projected_epc_uplift, -plans[pid].total_estimated_cost),
        )
        plan_b = plans[plan_b_id]
    else:
        # Only one package fits the budget - Plan B is Plan A itself.
        plan_b = plan_a

    return {
        "plans": {"plan_a": plan_a.model_dump(), "plan_b": plan_b.model_dump()},
        "budget": budget,
        "objective": objective,
        "comparison_rationale": (
            f"Comparing '{plan_a.title}' against '{plan_b.title}'. "
            "Plan A prioritises accessible envelope upgrades, while Plan B "
            "unlocks deeper decarbonisation with higher upfront capital "
            "expenditure."
        ),
    }
