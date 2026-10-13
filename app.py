"""FastAPI app serving the static dashboard and deterministic assessment API.

All scoring, retrofit, carbon/energy, and valuation numbers come from
src/engines/* - this app never computes them itself.
"""

import logging
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.engines.battle import estimate_package_score_uplift, get_battle_plans
from src.engines.carbon_energy import calculate_energy_and_carbon
from src.engines.retrofits import PropertyFeatures, RetrofitRecommender, apply_retrofits
from src.engines.scoring import (
    EpcRating,
    GlazingType,
    build_score_inputs,
    compute_green_home_score,
    insulation_level_to_condition,
)
from src.engines.valuation import estimate_value_uplift

# Load .env at module load so GEMINI_API_KEY (and GEMINI_MODEL) are
# reliably present in os.environ for every request - src/llm/advisor.py
# also loads it, but doing it here too means the key is available even
# if the advisor import path above falls back to the stub.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# LLM Advisor Import (Fallback provided in case src/llm/advisor.py is still being finalized)
try:
    from src.llm.advisor import generate_llm_explanation
except ImportError:
    def generate_llm_explanation(context_data: dict, user_message: str) -> str:
        score = context_data.get("green_home_score", {}).get("total_score", "N/A")
        band = context_data.get("green_home_score", {}).get("classification", "N/A")
        return (
            f"[Grounded Response] Your property has a Green Home Score of {score} ({band}). "
            f"All savings and uplift values are strictly derived from deterministic physical models."
        )

STATIC_DIR = Path(__file__).parent / "static"
DATA_DIR = Path(__file__).parent / "data"

app = FastAPI(title="Green Home Score & Retrofit Engine")

# 1. Enable CORS so frontend fetch() calls never fail
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")


# 2. Serve index.html directly on root (http://localhost:8000/)
@app.get("/")
def serve_root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Welcome to Green Home Score API. Static dashboard not found in /static."}


# 3. Customer ID Validation Endpoint (Section 9 & 10)
@app.get("/api/customer/{customer_id}")
def validate_customer(customer_id: str):
    csv_paths = [
        DATA_DIR / "synthetic_properties.csv",
        DATA_DIR / "synthetic_properties_full.csv",
        DATA_DIR / "train.csv",
    ]
    df = None
    for p in csv_paths:
        if p.exists():
            df = pd.read_csv(p)
            break

    if df is not None and "customer_id" in df.columns:
        match = df[df["customer_id"].astype(str).str.upper() == customer_id.strip().upper()]
        if not match.empty:
            row = match.iloc[0].to_dict()
            return {
                "valid": True,
                "customer_id": str(row.get("customer_id")),
                "property_id": str(row.get("property_id", "P10001")),
                "epc_rating": str(row.get("epc_rating", "E")),
                "insulation": str(row.get("insulation", "Poor")),
                "heating_type": str(row.get("heating_type", "Standard gas boiler")),
                "glazing": str(row.get("glazing", "Single")),
                "floor_area": float(row.get("floor_area", 95.0)),
                "baseline_elec_kwh": float(row.get("baseline_elec_kwh", 4800.0)),
                "baseline_gas_kwh": float(row.get("baseline_gas_kwh", 12000.0)),
                "current_value": float(row.get("current_value", 350000.0)),
                # Previously omitted entirely, so the frontend's
                # window.currentCustomerSolar/Smart always read undefined
                # and silently scored every customer as solar=False /
                # smart_controls=False regardless of the real record
                # (e.g. C03963, an EPC-B home with both, incorrectly
                # scored ~52/100 instead of 80+).
                "solar": bool(row.get("solar", False)),
                "smart_controls": bool(row.get("smart_controls", False)),
            }

    # No fallback to sample/default data here - an unknown customer_id is
    # always a 404, whether the dataset is missing or just doesn't
    # contain that ID. C03093/C00467 are real IDs in data/train.csv.
    raise HTTPException(
        status_code=404,
        detail=(
            f"Customer ID '{customer_id}' not found. Please enter a valid "
            "ID (e.g., C03093, C00467)."
        ),
    )


class AssessmentRequest(BaseModel):
    epc_rating: EpcRating
    insulation: Literal["Poor", "Moderate", "Good"]
    heating_type: str
    glazing: Literal["Single", "Double", "Triple"]
    solar: bool
    solar_pv_capacity_kwp: float = 0.0
    smart_controls: bool
    floor_area: float
    baseline_elec_kwh: float
    baseline_gas_kwh: float
    current_value: float
    target_epc: EpcRating | None = None


class AssessmentResponse(BaseModel):
    green_home_score: dict
    retrofit_recommendations: list
    full_retrofit_energy_carbon: dict
    valuation: dict


class WhatIfRequest(BaseModel):
    baseline_elec_kwh: float
    baseline_gas_kwh: float
    heating_type: str
    current_value: float
    epc_rating: EpcRating
    insulation: Literal["Poor", "Moderate", "Good"]
    glazing: Literal["Single", "Double", "Triple"]
    solar: bool
    smart_controls: bool
    floor_area: float
    selected_retrofits: list[str]
    target_epc: EpcRating | None = None


class WhatIfResponse(BaseModel):
    energy_carbon: dict
    valuation: dict
    green_home_score: dict


class ChatRequest(BaseModel):
    # property_summary/user_query are the original, still-supported
    # field names (see tests/test_llm.py::test_06_...); property_data/
    # user_question are accepted as aliases for the same thing, per the
    # frontend's payload shape. customer_id is optional and merged into
    # whichever property dict is used, so GeminiAdvisor.explain can
    # auto-resolve the customer's memory profile from it.
    property_summary: dict | None = None
    user_query: str = "Explain my score and recommendations"
    property_data: dict | None = None
    user_question: str | None = None
    customer_id: str | None = None


class BattleRequest(BaseModel):
    epc_rating: EpcRating
    insulation: Literal["Poor", "Moderate", "Good"]
    heating_type: str
    glazing: Literal["Single", "Double", "Triple"]
    solar: bool
    smart_controls: bool
    floor_area: float
    baseline_elec_kwh: float
    baseline_gas_kwh: float
    current_value: float
    budget: float | None = None
    objective: str = "carbon"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/assessment", response_model=AssessmentResponse)
def create_assessment(request: AssessmentRequest) -> AssessmentResponse:
    score_result = compute_green_home_score(
        build_score_inputs(
            epc_rating=request.epc_rating,
            insulation_level=request.insulation,
            heating_type=request.heating_type,
            glazing_type=GlazingType(request.glazing),
            solar=request.solar,
            smart_controls=request.smart_controls,
            elec_kwh=request.baseline_elec_kwh,
            gas_kwh=request.baseline_gas_kwh,
            floor_area_m2=request.floor_area,
        )
    )

    features = PropertyFeatures(
        insulation=request.insulation,
        heating=request.heating_type,
        glazing=request.glazing,
        solar=request.solar,
        smart_controls=request.smart_controls,
    )
    recommendations = RetrofitRecommender().recommend(features)

    energy_carbon = calculate_energy_and_carbon(
        baseline_elec=request.baseline_elec_kwh,
        baseline_gas=request.baseline_gas_kwh,
        retrofits_applied=[r.key for r in recommendations],
        property_features={
            "heating": request.heating_type,
            "insulation": insulation_level_to_condition(request.insulation),
            "glazing": GlazingType(request.glazing),
            "solar_kwp": request.solar_pv_capacity_kwp,
        },
    )

    valuation = estimate_value_uplift(
        request.current_value, request.epc_rating, target_epc=request.target_epc
    )

    return AssessmentResponse(
        green_home_score=score_result.model_dump(),
        retrofit_recommendations=[r.model_dump() for r in recommendations],
        full_retrofit_energy_carbon=energy_carbon.model_dump(),
        valuation=valuation.model_dump(),
    )


@app.post("/api/what-if", response_model=WhatIfResponse)
def run_what_if_scenario(req: WhatIfRequest) -> WhatIfResponse:
    energy_carbon = calculate_energy_and_carbon(
        baseline_elec=req.baseline_elec_kwh,
        baseline_gas=req.baseline_gas_kwh,
        retrofits_applied=req.selected_retrofits,
        property_features={
            "heating": req.heating_type,
            "insulation": insulation_level_to_condition(req.insulation),
            "glazing": GlazingType(req.glazing),
        },
    )

    valuation = estimate_value_uplift(
        req.current_value, req.epc_rating, target_epc=req.target_epc
    )

    before_score = compute_green_home_score(
        build_score_inputs(
            epc_rating=req.epc_rating,
            insulation_level=req.insulation,
            heating_type=req.heating_type,
            glazing_type=GlazingType(req.glazing),
            solar=req.solar,
            smart_controls=req.smart_controls,
            elec_kwh=req.baseline_elec_kwh,
            gas_kwh=req.baseline_gas_kwh,
            floor_area_m2=req.floor_area,
        )
    )

    new_insulation, new_heating_type, new_glazing, new_solar, new_smart_controls = (
        apply_retrofits(
            req.insulation,
            req.heating_type,
            req.glazing,
            req.solar,
            req.smart_controls,
            req.selected_retrofits,
        )
    )
    after_score = compute_green_home_score(
        build_score_inputs(
            epc_rating=req.epc_rating,
            insulation_level=new_insulation,
            heating_type=new_heating_type,
            glazing_type=GlazingType(new_glazing),
            solar=new_solar,
            smart_controls=new_smart_controls,
            elec_kwh=energy_carbon.post_elec,
            gas_kwh=energy_carbon.post_gas,
            floor_area_m2=req.floor_area,
        )
    )

    return WhatIfResponse(
        energy_carbon=energy_carbon.model_dump(),
        valuation=valuation.model_dump(),
        green_home_score={
            "before": before_score.model_dump(),
            "after": after_score.model_dump(),
            "score_uplift": after_score.score - before_score.score,
        },
    )


@app.post("/api/chat")
def chat_with_advisor(req: ChatRequest) -> dict:
    context_data = req.property_data or req.property_summary or {}
    if req.customer_id and "customer_id" not in context_data:
        context_data = {**context_data, "customer_id": req.customer_id}
    user_message = req.user_question or req.user_query

    try:
        explanation = generate_llm_explanation(
            context_data=context_data,
            user_message=user_message,
        )
    except Exception:
        logger.exception("Advisor call failed; returning clean fallback reply.")
        explanation = (
            "The AI advisor is temporarily unavailable. Your computed property "
            "figures above are unaffected - please try asking again shortly."
        )
    return {"reply": explanation}


@app.post("/api/plans/battle")
def battle_plans(req: BattleRequest) -> dict:
    result = get_battle_plans(budget=req.budget, objective=req.objective)
    # Attach a live Green Home Score before/after/uplift for this specific
    # property to each selected plan - never a fixed/default baseline.
    for plan in (result.get("plans") or {}).values():
        plan.update(
            estimate_package_score_uplift(
                plan["plan_id"],
                epc_rating=req.epc_rating,
                insulation_level=req.insulation,
                heating_type=req.heating_type,
                glazing_type=req.glazing,
                solar=req.solar,
                smart_controls=req.smart_controls,
                baseline_elec=req.baseline_elec_kwh,
                baseline_gas=req.baseline_gas_kwh,
                floor_area_m2=req.floor_area,
            )
        )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)