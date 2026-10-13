# Project: Megathon X - Lloyds Green Home Score & Retrofit Engine (PS2)

## 1. System Architecture & Core Stack
- Frontend & UI: Streamlit (interactive multi-tab app, what-if sliders, charts).
- Backend / DB: Local SQLite with SQLAlchemy (Multi-user data isolation, properties, assessments, chat history).
- Scoring / Analytics: Scikit-learn / XGBoost regression, deterministic formulas, numpy/pandas.
- GenAI: Gemini 2.5 Flash / Claude for grounded explanations strictly from computed JSON.

## 2. Mathematical Scoring & Physics Constraints (STRICT)
- The LLM MUST NEVER calculate scores, carbon figures, or property uplifts directly.
- Score Formula: S = round(sum(w_k * s_k)) from 0 to 100 across 7 fixed weights:
  1. Energy efficiency (EPC rating): 25%
  2. Energy consumption intensity (kWh/m²): 20%
  3. Insulation (Poor/Mod/Good): 15%
  4. Heating system (Heat pump/Gas/Old): 15%
  5. Glazing (Single/Double/Triple): 10%
  6. Renewable energy (Solar PV): 10%
  7. Smart energy management: 5%
- Classification: 80-100 Highly efficient, 65-79 Good, 50-64 Moderate, 30-49 Poor, 0-29 Very poor.
- Retrofit Sequencing: Insulation MUST be prioritized before heat pump recommendations.
- Fuel Decoupling: Heat pumps decrease gas to 0 but increase grid electricity. Compute separate deltas.
- Carbon Engine: delta_C = delta_E_elec * 0.207 + delta_E_gas * 0.183 (kgCO2e).
- Valuation Uplift: Trained regression model predicting an indicative range (+2% to +5%), not a single point estimate.

## 3. Strict Megathon Deliverable Deadlines & Guidelines
- M1 (10:00 PM, 10th Oct): deliverables/M1.pdf (Max 2 pages, double-blind: Team Number only, NO personal/college names).
- M2 (4:00 AM, 11th Oct): deliverables/M2.pdf (Max 2 pages) + git push to main.
- Final (11:00 AM, 11th Oct): deliverables/final_report.pdf, README.md (run commands only), MIT LICENSE, 4-min video link.