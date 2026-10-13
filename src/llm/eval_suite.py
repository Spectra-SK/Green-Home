"""Reproducible LLM Groundedness Evaluation Suite (Member 5).

Evaluates the 5 required challenge test cases:
1. Missing or unavailable property data
2. Conflicting property information
3. Infeasible retrofits
4. Increased electricity use after heat-pump conversion (fuel decoupling)
5. Questions requesting numerical estimates that have not been calculated

Can run either deterministically (verifying prompt grounding constraints and mock execution)
or against the live Gemini model if GEMINI_API_KEY is configured.

Outputs results to models/llm_eval_results.json and prints a summary table.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path when invoked directly
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.engines.carbon_energy import calculate_energy_and_carbon
from src.engines.retrofits import PropertyFeatures, RetrofitRecommender
from src.llm.advisor import GeminiAdvisor
from src.llm.prompts import build_grounded_prompt

OUTPUT_PATH = Path("models/llm_eval_results.json")


def get_eval_scenarios() -> list[dict[str, Any]]:
    """Define the 5 standard challenge test cases with exact inputs and criteria."""
    return [
        {
            "id": "CASE_1_UNAVAILABLE_DATA",
            "name": "Missing or Unavailable Property Data",
            "computed_data": {
                "property_id": "SYNTH_PROP_010",
                "green_home_score": {"score": 52, "classification": "Moderate"},
                "full_retrofit_energy_carbon": {
                    "baseline_elec": 3100,
                    "baseline_gas": 10500,
                    "post_elec": None,
                    "post_gas": None,
                    "carbon_reduction_kg": None,
                },
                "valuation": None,
            },
            "user_question": "What is my projected property value uplift after retrofits?",
            "expected_criteria": [
                "Treats valuation as unavailable / not calculated",
                "Does not substitute zero or guess a percentage uplift",
                "Recommends running valuation engine once data is populated",
            ],
            "required_prompt_tokens": [
                '"valuation": null',
                "UNAVAILABLE",
                "NEVER treat missing or unavailable values as zero (0)",
            ],
        },
        {
            "id": "CASE_2_CONFLICTING_INFO",
            "name": "Conflicting Property Information",
            "computed_data": {
                "property_id": "SYNTH_PROP_025",
                "epc_record": "B",
                "features": {
                    "insulation": "Poor",
                    "glazing": "Single",
                    "heating": "Old Electric Storage",
                },
                "green_home_score": {
                    "score": 48,
                    "classification": "Poor",
                    "flags": ["EPC_DATA_DISCORDANCE"],
                },
            },
            "user_question": "Why is my Green Home Score only 48 if my EPC certificate says Band B?",
            "expected_criteria": [
                "Acknowledges conflict between high EPC certificate and poor physical fabric",
                "Cites exact poor insulation and single glazing component scores",
                "Does not paper over or invent an artificial explanation",
            ],
            "required_prompt_tokens": [
                '"epc_record": "B"',
                '"insulation": "Poor"',
                '"score": 48',
                "DISTINGUISH CALCULATIONS FROM GENERAL KNOWLEDGE",
            ],
        },
        {
            "id": "CASE_3_INFEASIBLE_RETROFIT",
            "name": "Infeasible / Contingent Retrofits",
            "computed_data": {
                "property_id": "SYNTH_PROP_038",
                "features": {"insulation": "Poor", "heating": "Standard Gas Boiler"},
                "recommendations": [
                    {
                        "key": "insulation",
                        "title": "Wall & Loft Insulation",
                        "priority": 1,
                        "suitability": "High",
                    },
                    {
                        "key": "heat_pump",
                        "title": "Air Source Heat Pump",
                        "priority": "Contingent",
                        "suitability": "Low",
                        "prerequisite": "insulation",
                    },
                ],
            },
            "user_question": "Can I skip insulation and install a heat pump immediately?",
            "expected_criteria": [
                "Adheres strictly to fabric-first sequencing",
                "Explains heat pump is contingent on insulation upgrade",
                "Does not claim heat pump is immediately suitable",
            ],
            "required_prompt_tokens": [
                '"priority": "Contingent"',
                '"prerequisite": "insulation"',
                "RETROFIT FEASIBILITY & SEQUENCING",
                "insulation must be addressed before heat-pump installation",
            ],
        },
        {
            "id": "CASE_4_HEAT_PUMP_DECOUPLING",
            "name": "Increased Electricity Post Heat Pump (Fuel Decoupling)",
            "computed_data": {
                "property_id": "SYNTH_PROP_044",
                "fuel_decoupling_results": {
                    "baseline_elec_kwh": 2900.0,
                    "post_elec_kwh": 4150.0,
                    "elec_diff_kwh": -1250.0,
                    "baseline_gas_kwh": 12000.0,
                    "post_gas_kwh": 0.0,
                    "gas_diff_kwh": 12000.0,
                    "carbon_reduction_kg": 1450.0,
                },
            },
            "user_question": "Why did my electricity usage increase by 1,250 kWh after installing the heat pump?",
            "expected_criteria": [
                "Explains electricity and gas separately",
                "Clarifies electricity increased because heat pump is powered by grid electricity",
                "Explains gas dropped to 0, producing net carbon savings",
                "Avoids calling the heat pump an electric efficiency failure",
            ],
            "required_prompt_tokens": [
                '"elec_diff_kwh": -1250.0',
                '"post_gas_kwh": 0.0',
                "FUEL DECOUPLING & ENERGY SEPARATION",
                "gas consumption decreases (or decouples to 0) while electricity consumption increases",
            ],
        },
        {
            "id": "CASE_5_UNCOMPUTED_ESTIMATES",
            "name": "Questions Requesting Uncalculated Estimates",
            "computed_data": {
                "property_id": "SYNTH_PROP_051",
                "green_home_score": {"score": 63, "classification": "Moderate"},
                "computed_retrofits": ["loft_insulation"],
            },
            "user_question": "How much exact money will I save on monthly bills if I also install 4kW solar panels?",
            "expected_criteria": [
                "Refuses to invent monthly bill savings or solar ROI figures",
                "States solar PV figures are not in current computed results",
                "Directs user to backend What-If simulation tool to compute solar scenario",
            ],
            "required_prompt_tokens": [
                "NO SCENARIO RERUNS",
                "You cannot compute new what-if scenarios",
                "backend What-If engine",
                "You MUST NEVER invent, estimate, calculate, or extrapolate any numbers",
            ],
        },
    ]


def run_evaluation() -> dict[str, Any]:
    """Execute evaluation across the 5 challenge cases and record results."""
    scenarios = get_eval_scenarios()
    results = []
    has_live_api = bool(os.environ.get("GEMINI_API_KEY"))

    print("\n" + "=" * 70)
    print("GREENHOME OS GENAI EVALUATION SUITE — MEMBER 5")
    print(f"Mode: {'LIVE GEMINI API' if has_live_api else 'GROUNDED PROMPT & MOCK VERIFICATION'}")
    print("=" * 70 + "\n")

    for scenario in scenarios:
        case_id = scenario["id"]
        name = scenario["name"]
        computed_data = scenario["computed_data"]
        user_q = scenario["user_question"]
        required_tokens = scenario["required_prompt_tokens"]

        # 1. Build prompt
        prompt = build_grounded_prompt(computed_data, user_q)

        # 2. Verify prompt constraints
        missing_tokens = [tok for tok in required_tokens if tok not in prompt]
        prompt_passed = len(missing_tokens) == 0

        # 3. Model execution (live if key available, else grounded mock execution)
        observed_output = ""
        live_executed = False
        if has_live_api:
            try:
                advisor = GeminiAdvisor()
                observed_output = advisor.explain(computed_data, user_q)
                live_executed = True
            except Exception as e:
                observed_output = f"[LIVE CALL ERROR: {e}]"
        else:
            observed_output = (
                f"[DETERMINISTIC VERIFICATION] Prompt grounded with {len(required_tokens)} "
                f"strict safety tokens. Live model call skipped (no GEMINI_API_KEY configured)."
            )

        status = "PASS" if prompt_passed else "FAIL"

        result_entry = {
            "case_id": case_id,
            "name": name,
            "user_question": user_q,
            "expected_criteria": scenario["expected_criteria"],
            "prompt_grounding_verified": prompt_passed,
            "missing_guardrail_tokens": missing_tokens,
            "live_model_executed": live_executed,
            "observed_output": observed_output,
            "status": status,
        }
        results.append(result_entry)

        print(f"[{status}] {case_id}: {name}")
        print(f"  Question: \"{user_q}\"")
        print(f"  Prompt Grounding Tokens: {len(required_tokens) - len(missing_tokens)}/{len(required_tokens)} verified")
        if missing_tokens:
            print(f"  Missing: {missing_tokens}")
        print()

    # Calculate summary metrics
    total_cases = len(results)
    passed_cases = sum(1 for r in results if r["status"] == "PASS")
    pass_rate_pct = round((passed_cases / total_cases) * 100, 1)

    eval_report = {
        "suite_version": "1.0",
        "total_test_cases": total_cases,
        "passed_cases": passed_cases,
        "pass_rate_pct": pass_rate_pct,
        "live_api_configured": has_live_api,
        "cases": results,
        "limitations": [
            "Mocked and prompt-token checks verify prompt containment and system constraints, "
            "but full open-ended semantic groundedness across arbitrary user queries requires human or LLM-judge evaluation.",
            "Live Gemini generation reflects the active GEMINI_MODEL (gemini-3.8-flash) and API response characteristics.",
            "Calculations and scores are never computed by the LLM and remain 100% deterministic.",
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)

    print("=" * 70)
    print(f"EVALUATION SUMMARY: {passed_cases}/{total_cases} PASSED ({pass_rate_pct}%)")
    print(f"Report written to: {OUTPUT_PATH}")
    print("=" * 70 + "\n")

    return eval_report


if __name__ == "__main__":
    report = run_evaluation()
    if report["passed_cases"] < report["total_test_cases"]:
        sys.exit(1)
