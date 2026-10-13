/**
 * GreenHome AI · Client Pipeline Engine
 * Features:
 *   - Login Canvas (Deep Oceanic Blue & Cyan Theme, matching the dashboard)
 *   - Dashboard Persistent Canvas (Deep Oceanic Blue & Cyan Theme)
 *   - Strict Customer Validation & Typewriter Welcome
 *   - Full Teammate API Integration (/api/customer, /api/assessment, /api/what-if, /api/plans/battle, /api/chat)
 */

  window.currentCustomerSolar = false;
  window.currentCustomerSmart = false;

// 1. Blue/Cyan Login Overlay Canvas
function initLoginCanvas() {
  const c = document.getElementById('loginBgCanvas');
  if (!c) return;
  const x = c.getContext('2d');
  let W, H, dpr, t = 0;
  let animId;
  const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let orbs = [], pts = [];

  function rnd(a, b) { return a + Math.random() * (b - a); }
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = c.width = window.innerWidth * dpr;
    H = c.height = window.innerHeight * dpr;
    orbs = [];
    for (let i = 0; i < 4; i++) {
      orbs.push({ x: rnd(0, W), y: rnd(0, H), r: rnd(0.3, 0.55) * Math.max(W, H), p: rnd(0, 6.28), s: rnd(0.0004, 0.0009), h: i % 2 });
    }
    const n = Math.round(Math.min(80, (W * H) / (dpr * dpr) / 14000));
    pts = [];
    for (let i = 0; i < n; i++) {
      pts.push({ x: rnd(0, W), y: rnd(0, H), vx: rnd(-0.25, 0.25) * dpr, vy: rnd(-0.4, -0.08) * dpr, r: rnd(1.2, 2.5) * dpr });
    }
  }

  function frame() {
    t++;
    const g = x.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, '#071724');
    g.addColorStop(1, '#0c2236');
    x.globalCompositeOperation = 'source-over';
    x.fillStyle = g;
    x.fillRect(0, 0, W, H);
    x.globalCompositeOperation = 'lighter';

    orbs.forEach(o => {
      const ox = o.x + Math.sin(t * o.s * 8 + o.p) * W * 0.12;
      const oy = o.y + Math.cos(t * o.s * 6 + o.p) * H * 0.12;
      const rg = x.createRadialGradient(ox, oy, 0, ox, oy, o.r);
      const col = o.h ? '0, 210, 255' : '56, 189, 248';
      rg.addColorStop(0, `rgba(${col}, 0.18)`);
      rg.addColorStop(1, `rgba(${col}, 0)`);
      x.fillStyle = rg;
      x.fillRect(0, 0, W, H);
    });

    const link = 140 * dpr;
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i];
      if (!still) { a.x += a.vx; a.y += a.vy; }
      if (a.y < -10) { a.y = H + 10; a.x = rnd(0, W); }
      if (a.x < -10) a.x = W + 10;
      if (a.x > W + 10) a.x = -10;
      for (let j = i + 1; j < pts.length; j++) {
        const b = pts[j], dx = a.x - b.x, dy = a.y - b.y, d = dx * dx + dy * dy;
        if (d < link * link) {
          x.strokeStyle = `rgba(0, 180, 240, ${0.35 * (1 - Math.sqrt(d) / link)})`;
          x.lineWidth = dpr;
          x.beginPath();
          x.moveTo(a.x, a.y);
          x.lineTo(b.x, b.y);
          x.stroke();
        }
      }
      const pulse = 0.55 + 0.45 * Math.sin(t * 0.03 + i);
      x.fillStyle = `rgba(0, 194, 255, ${0.55 * pulse})`;
      x.beginPath();
      x.arc(a.x, a.y, a.r, 0, 6.283);
      x.fill();
    }
    if (!still) animId = requestAnimationFrame(frame);
  }

  window.addEventListener('resize', resize);
  resize();
  frame();

  window.stopLoginAnimation = () => {
    if (animId) cancelAnimationFrame(animId);
    window.removeEventListener('resize', resize);
  };
}

// 2. Persistent Deep Blue / Cyan Dashboard Canvas
function initDashboardCanvas() {
  const c = document.getElementById('dashboardBgCanvas');
  if (!c) return;
  const x = c.getContext('2d');
  let W, H, dpr, t = 0;
  const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let orbs = [], pts = [];

  function rnd(a, b) { return a + Math.random() * (b - a); }
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = c.width = window.innerWidth * dpr;
    H = c.height = window.innerHeight * dpr;
    orbs = [];
    for (let i = 0; i < 4; i++) {
      orbs.push({ x: rnd(0, W), y: rnd(0, H), r: rnd(0.35, 0.6) * Math.max(W, H), p: rnd(0, 6.28), s: rnd(0.0003, 0.0007), h: i % 2 });
    }
    const n = Math.round(Math.min(75, (W * H) / (dpr * dpr) / 16000));
    pts = [];
    for (let i = 0; i < n; i++) {
      pts.push({ x: rnd(0, W), y: rnd(0, H), vx: rnd(-0.2, 0.2) * dpr, vy: rnd(-0.35, -0.08) * dpr, r: rnd(1.2, 2.8) * dpr });
    }
  }

  function frame() {
    t++;
    // Midnight Blue Ocean Base
    const g = x.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, '#071724');
    g.addColorStop(1, '#0c2236');
    x.globalCompositeOperation = 'source-over';
    x.fillStyle = g;
    x.fillRect(0, 0, W, H);
    x.globalCompositeOperation = 'lighter';

    // Ambient Cyan & Ice Blue Orbs
    orbs.forEach(o => {
      const ox = o.x + Math.sin(t * o.s * 8 + o.p) * W * 0.1;
      const oy = o.y + Math.cos(t * o.s * 6 + o.p) * H * 0.1;
      const rg = x.createRadialGradient(ox, oy, 0, ox, oy, o.r);
      const col = o.h ? '0, 210, 255' : '56, 189, 248';
      rg.addColorStop(0, `rgba(${col}, 0.13)`);
      rg.addColorStop(1, `rgba(${col}, 0)`);
      x.fillStyle = rg;
      x.fillRect(0, 0, W, H);
    });

    const link = 135 * dpr;
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i];
      if (!still) { a.x += a.vx; a.y += a.vy; }
      if (a.y < -10) { a.y = H + 10; a.x = rnd(0, W); }
      if (a.x < -10) a.x = W + 10;
      if (a.x > W + 10) a.x = -10;
      for (let j = i + 1; j < pts.length; j++) {
        const b = pts[j], dx = a.x - b.x, dy = a.y - b.y, d = dx * dx + dy * dy;
        if (d < link * link) {
          x.strokeStyle = `rgba(56, 189, 248, ${0.18 * (1 - Math.sqrt(d) / link)})`;
          x.lineWidth = dpr * 0.8;
          x.beginPath();
          x.moveTo(a.x, a.y);
          x.lineTo(b.x, b.y);
          x.stroke();
        }
      }
      const pulse = 0.5 + 0.5 * Math.sin(t * 0.03 + i);
      x.fillStyle = `rgba(0, 229, 255, ${0.5 * pulse})`;
      x.beginPath();
      x.arc(a.x, a.y, a.r, 0, 6.283);
      x.fill();
    }
    if (!still) requestAnimationFrame(frame);
  }

  window.addEventListener('resize', resize);
  resize();
  frame();
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();
  initLoginCanvas();
  initDashboardCanvas();

  let activeUpgrades = new Set(["loft_insulation", "heat_pump"]);
  let currentObjective = "carbon";

  const loginOverlay = document.getElementById("loginOverlay");
  const loginCard = document.getElementById("loginCard");
  const loginForm = document.getElementById("loginForm");
  const loginSprout = document.getElementById("loginSprout");
  const btnLoginSubmit = document.getElementById("btnLoginSubmit");
  const btnLogout = document.getElementById("btnLogout");
  const appLayout = document.getElementById("appLayout");
  const userSessionDisplay = document.getElementById("userSessionDisplay");
  const loginErrorMsg = document.getElementById("loginErrorMsg");
  const inputWrapper = document.getElementById("inputWrapper");

  window.currentAssessmentData = null;
  window.currentCustomerId = null;

  const UPGRADE_TO_LEVER = {
    loft_insulation: "insulation",
    double_glazing: "glazing",
    heat_pump: "heat_pump",
    solar_panels: "solar_pv",
    smart_thermostat: "smart_controls"
  };

  const OBJECTIVE_TO_BACKEND = { carbon: "carbon", bills: "energy", value: "score" };

  const upgradesList = [
    {
      id: "loft_insulation",
      name: "Loft & Roof Insulation",
      desc: "Puts a warm winter hat on your house to stop heat leaking out.",
      priority: "High Priority",
      impact: "Illustrative space-heating demand reduction",
      icon: "home"
    },
    {
      id: "double_glazing",
      name: "Double / Triple Glazing",
      desc: "Replaces drafty single glass with sealed double glass.",
      priority: "Medium Priority",
      impact: "Illustrative space-heating demand reduction",
      icon: "panels-top-left"
    },
    {
      id: "heat_pump",
      name: "Air-Source Heat Pump",
      desc: "Replaces dirty gas boiler with clean outside air heating.",
      priority: "High Priority",
      impact: "Gas use may fall while electricity use may rise",
      icon: "thermometer-sun"
    },
    {
      id: "solar_panels",
      name: "Rooftop Solar PV",
      desc: "Generates free electricity from sunlight to power your heat pump.",
      priority: "Medium Priority",
      impact: "May reduce grid electricity imports",
      icon: "sun"
    },
    {
      id: "smart_thermostat",
      name: "Smart Heating Controls",
      desc: "Turns off heat in empty rooms and follows your routine.",
      priority: "Quick Win",
      impact: "May reduce heating energy use",
      icon: "activity"
    }
  ];

  function _flatten(s) {
    return String(s).toLowerCase().replace(/[-_\s]/g, "");
  }

  function _hasWord(haystack, word) {
    const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`\\b${escaped}\\b`).test(haystack);
  }

  function setSelectValueFuzzy(selectEl, rawValue) {
    if (!selectEl || rawValue === null || rawValue === undefined || rawValue === "") {
      return false;
    }
    const targetFlat = _flatten(rawValue);

    for (const option of selectEl.options) {
      if (_flatten(option.value) === targetFlat || _flatten(option.textContent) === targetFlat) {
        selectEl.value = option.value;
        return true;
      }
    }

    const targetTokens = String(rawValue)
      .toLowerCase()
      .replace(/[-_]/g, " ")
      .split(/\s+/)
      .filter(tok => tok.length > 2);

    if (targetTokens.length) {
      for (const option of selectEl.options) {
        const haystack = `${option.value} ${option.textContent}`.toLowerCase();
        if (targetTokens.every(tok => _hasWord(haystack, tok))) {
          selectEl.value = option.value;
          return true;
        }
      }
    }

    return false;
  }

  function triggerLoginShake(message) {
    loginCard.classList.remove("shake");
    void loginCard.offsetWidth;
    loginCard.classList.add("shake");

    inputWrapper.classList.add("error-state");
    loginErrorMsg.textContent = message;
    loginErrorMsg.style.display = "block";

    btnLoginSubmit.disabled = false;
    btnLoginSubmit.innerHTML = '<span>Access Eco Portal</span> <i data-lucide="arrow-right"></i>';
    if (window.lucide) window.lucide.createIcons();
  }

  // 1. Eco Login (Green Sprout -> Typewriter -> Reveals Blue Dashboard)
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const custId = document.getElementById("loginCustId").value.trim().toUpperCase();

      inputWrapper.classList.remove("error-state");
      loginErrorMsg.style.display = "none";

      if (!custId) {
        triggerLoginShake("Please enter a Customer ID.");
        return;
      }

      btnLoginSubmit.disabled = true;
      btnLoginSubmit.innerHTML = '<span>Verifying Lloyds Records...</span>';

      try {
        const checkRes = await fetch(`/api/customer/${custId}`);
        if (!checkRes.ok) {
          throw new Error(`Customer ID '${custId}' not found.`);
        }
        const custData = await checkRes.json();

        const rawHeating = custData.heating_type || custData.heating_system || "";
        setSelectValueFuzzy(document.getElementById("epcRating"), custData.epc_rating);
        setSelectValueFuzzy(document.getElementById("insulation"), custData.insulation);
        setSelectValueFuzzy(document.getElementById("heatingType"), rawHeating);
        setSelectValueFuzzy(document.getElementById("glazing"), custData.glazing);
        if (custData.floor_area) document.getElementById("floorArea").value = custData.floor_area;
        if (custData.current_value) document.getElementById("currentValue").value = custData.current_value;
        if (custData.baseline_elec_kwh) document.getElementById("baselineElec").value = custData.baseline_elec_kwh;
        if (custData.baseline_gas_kwh) document.getElementById("baselineGas").value = custData.baseline_gas_kwh;

        // This customer's real solar/smart-controls status, read from the
        // actual dataset row - getInputs() depends on these globals, so a
        // wrong or stale value here silently mis-scores every assessment
        // for this login (e.g. a solar customer always scoring
        // renewable_energy=0).
        window.currentCustomerSolar = custData.solar === true || String(custData.solar).toLowerCase() === "true";
        window.currentCustomerSmart = custData.smart_controls === true || String(custData.smart_controls).toLowerCase() === "true";

        window.currentCustomerId = custId;
        userSessionDisplay.textContent = `Customer: ${custId}`;

        loginSprout.classList.add("sprouting");

        setTimeout(() => {
          document.getElementById("loginFormContainer").style.display = "none";
          const twContainer = document.getElementById("typewriterContainer");
          twContainer.style.display = "block";

          const textTarget = document.getElementById("typewriterText");
          const welcomeMessage = `Welcome, ${custId}! 🌱`;
          let charIndex = 0;

          const typeInterval = setInterval(() => {
            if (charIndex < welcomeMessage.length) {
              textTarget.textContent += welcomeMessage.charAt(charIndex);
              charIndex++;
            } else {
              clearInterval(typeInterval);

              setTimeout(() => {
                loginOverlay.classList.add("hidden");
                appLayout.classList.remove("collapsing");
                if (window.stopLoginAnimation) window.stopLoginAnimation();

                runAssessment();

                setTimeout(() => {
                  loginSprout.classList.remove("sprouting");
                  document.getElementById("loginFormContainer").style.display = "block";
                  twContainer.style.display = "none";
                  textTarget.textContent = "";
                  btnLoginSubmit.disabled = false;
                  btnLoginSubmit.innerHTML = '<span>Access Eco Portal</span> <i data-lucide="arrow-right"></i>';
                  if (window.lucide) window.lucide.createIcons();
                }, 600);
              }, 450);
            }
          }, 50);

        }, 400);

      } catch (err) {
        triggerLoginShake(
          `Invalid Customer ID '${custId}'. Please check and try again (e.g. C03093, C00467).`
        );
      }
    });
  }

  // 2. Logout Decay / Collapse Animation
  if (btnLogout) {
    btnLogout.addEventListener("click", () => {
      appLayout.classList.add("collapsing");

      const assessmentForm = document.getElementById("assessmentForm");
      if (assessmentForm) assessmentForm.reset();
      window.currentAssessmentData = null;
      window.currentCustomerId = null;
      window.currentBaselineScore = null;
      window.currentCustomerSolar = false;
      window.currentCustomerSmart = false;
      applyCurrentScoreToUI(null);
      activeUpgrades = new Set(["loft_insulation", "heat_pump"]);
      renderUpgrades();
      const loginCustIdInput = document.getElementById("loginCustId");
      if (loginCustIdInput) loginCustIdInput.value = "";
      if (userSessionDisplay) userSessionDisplay.textContent = "";

      setTimeout(() => {
        loginOverlay.classList.remove("hidden");
        if (window.lucide) window.lucide.createIcons();
        initLoginCanvas();
      }, 600);
    });
  }

  // 3. Render Upgrade Checkboxes
  function renderUpgrades() {
    const container = document.getElementById("upgradesStack");
    container.innerHTML = upgradesList.map(item => {
      const isChecked = activeUpgrades.has(item.id);
      return `
        <div class="upgrade-item ${isChecked ? 'active' : ''}">
          <div class="up-left">
            <div class="up-icon"><i data-lucide="${item.icon}"></i></div>
            <div>
              <div class="up-title">${item.name}</div>
              <div class="up-desc">${item.desc}</div>
              <div class="up-chips">
                <span class="chip priority">${item.priority}</span>
                <span class="chip impact">${item.impact}</span>
              </div>
            </div>
          </div>
          <label class="switch">
            <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="window.toggleUpgrade('${item.id}')">
            <span class="slider"></span>
          </label>
        </div>
      `;
    }).join("");
    if (window.lucide) window.lucide.createIcons();
  }

  window.toggleUpgrade = function(id) {
    if (activeUpgrades.has(id)) {
      activeUpgrades.delete(id);
    } else {
      activeUpgrades.add(id);
    }
    renderUpgrades();
    runWhatIfSimulation();
  };

  // 4. Render 7 Component Sub-scores
  function renderSubScores(components) {
    const container = document.getElementById("factorsGrid");
    const labelMap = {
      epc_rating: "Energy Rating (EPC)",
      energy_intensity: "Energy Use per m²",
      insulation: "Insulation Performance",
      heating: "Heating Technology",
      glazing: "Windows and Glazing",
      renewable_energy: "Renewable Generation",
      smart_controls: "Smart Energy Management"
    };

    container.innerHTML = Object.entries(components).map(([k, v]) => {
      const score = Math.round(v);
      const tone = score >= 65 ? "good" : score <= 35 ? "poor" : "";
      return `
        <div class="factor-card">
          <div class="factor-card-head">
            <span>${labelMap[k] || k}</span>
            <span>${score}/100</span>
          </div>
          <div class="bar-track-back">
            <div class="bar-track-fill ${tone}" style="width: ${score}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  }

  function getInputs() {
    return {
      epc_rating: document.getElementById("epcRating").value,
      insulation: document.getElementById("insulation").value,
      heating_type: document.getElementById("heatingType").value,
      glazing: document.getElementById("glazing").value,
      solar: window.currentCustomerSolar,
      solar_pv_capacity_kwp: window.currentCustomerSolar ? 3.5 : 0.0,
      smart_controls: window.currentCustomerSmart,
      floor_area: parseFloat(document.getElementById("floorArea").value) || 47.5,
      current_value: parseFloat(document.getElementById("currentValue").value) || 198600.0,
      baseline_elec_kwh: parseFloat(document.getElementById("baselineElec").value) || 1912.6,
      baseline_gas_kwh: parseFloat(document.getElementById("baselineGas").value) || 0.0
    };
  }

  window.currentBaselineScore = null;

  function _formatBandLabel(hasScore, band) {
    if (!hasScore) return "No Data";
    if (!band) return "Unknown";
    return /efficient/i.test(band) ? band : `${band} Efficiency`;
  }

  function _applyScoreToDial(valEl, bandEl, scoreResult) {
    const hasScore = scoreResult && typeof scoreResult.score === "number";
    const total = hasScore ? scoreResult.score : "—";
    valEl.textContent = total;
    bandEl.textContent = _formatBandLabel(hasScore, scoreResult && scoreResult.classification);
    bandEl.className = `score-badge ${hasScore && total >= 65 ? "good" : "poor"}`;
    return hasScore ? total : null;
  }

  function applyCurrentScoreToUI(scoreResult) {
    const total = _applyScoreToDial(
      document.getElementById("heroScoreVal"),
      document.getElementById("heroScoreBand"),
      scoreResult
    );
    window.currentBaselineScore = total;

    if (scoreResult && scoreResult.component_scores) {
      renderSubScores(scoreResult.component_scores);
    }
    renderAdvisorSummary(scoreResult);

    applyPotentialScoreToUI(scoreResult);
  }

  function applyPotentialScoreToUI(scoreResult) {
    const total = _applyScoreToDial(
      document.getElementById("potentialScoreVal"),
      document.getElementById("potentialScoreBand"),
      scoreResult
    );

    const pill = document.getElementById("scoreUpliftPill");
    const baseline = window.currentBaselineScore;
    if (typeof total === "number" && typeof baseline === "number") {
      const uplift = total - baseline;
      pill.textContent = `${uplift >= 0 ? "+" : ""}${uplift} pts`;
      pill.className = `uplift-pill ${uplift > 0 ? "positive" : uplift < 0 ? "negative" : ""}`;
    } else {
      pill.textContent = "+0 pts";
      pill.className = "uplift-pill";
    }
  }

  function getCurrentScore() {
    if (typeof window.currentBaselineScore === "number") return window.currentBaselineScore;
    const displayed = parseInt(document.getElementById("heroScoreVal")?.textContent, 10);
    return Number.isFinite(displayed) ? displayed : 0;
  }

  function renderAdvisorSummary(scoreResult) {
    const reply = document.getElementById("aiAdvisorReply");
    if (!reply || !scoreResult || typeof scoreResult.score !== "number") return;

    const labelMap = {
      epc_rating: "the EPC rating",
      energy_intensity: "energy use per m²",
      insulation: "insulation",
      heating: "the heating system",
      glazing: "glazing",
      renewable_energy: "renewable generation",
      smart_controls: "smart controls"
    };

    let weakestPhrase = "";
    if (scoreResult.component_scores) {
      const entries = Object.entries(scoreResult.component_scores)
        .filter(([, v]) => typeof v === "number")
        .sort((a, b) => a[1] - b[1]);
      if (entries.length) {
        weakestPhrase = ` primarily due to ${labelMap[entries[0][0]] || entries[0][0]}`;
      }
    }

    reply.innerHTML =
      `"Your property scored <strong>${scoreResult.score}/100 (${scoreResult.classification})</strong>` +
      `${weakestPhrase}. Use the Upgrade Simulator or Package Comparison below to see how specific ` +
      `retrofits change your score, energy bills, carbon footprint, and property value."`;
  }

  // Builds the single, unambiguous structured object sent to the AI
  // Advisor - never the raw /api/assessment or /api/what-if response
  // shape directly, since those differ (one is flat, the other nests
  // {before, after}) and forwarding whichever one last ran risks the
  // model latching onto the wrong "current" score. This is built fresh
  // from the latest /api/what-if response (which always recomputes
  // both the before/after score and the before/after energy figures for
  // the CURRENTLY selected upgrades), so it can never carry a stale
  // scenario from a previous toggle.
  function buildAdvisorContext(whatIfData) {
    const before = whatIfData.green_home_score && whatIfData.green_home_score.before;
    const after = whatIfData.green_home_score && whatIfData.green_home_score.after;
    const energyCarbon = whatIfData.energy_carbon || {};
    const valuation = whatIfData.valuation || {};
    const selectedRetrofits = Array.from(activeUpgrades);

    const limitations = [
      "Property and customer data are synthetic demo records, not real customer accounts.",
      "The property-value estimate is a modelled statistical association, not a guaranteed sale price.",
      "Retrofit cost and impact figures are illustrative engineering estimates, not site-survey quotes.",
    ];
    if (!window.currentCustomerSolar && !selectedRetrofits.includes("solar_panels")) {
      limitations.push("No solar PV is currently installed or selected, so renewable_energy scores 0.");
    }

    return {
      customer_id: window.currentCustomerId || null,
      // The score actually shown in the Overview hero ring right now -
      // this is the property's CURRENT (pre-selected-upgrade) score.
      current_score: before ? before.score : null,
      current_score_classification: before ? before.classification : null,
      current_component_scores: before ? before.component_scores : null,
      component_weights: before ? before.weights : null,
      // The score if the currently toggled-on upgrades below were applied.
      selected_retrofits: selectedRetrofits,
      potential_score_with_selected_retrofits: after ? after.score : null,
      potential_score_classification: after ? after.classification : null,
      potential_component_scores: after ? after.component_scores : null,
      baseline_electricity_kwh: energyCarbon.baseline_elec ?? null,
      proposed_electricity_kwh: energyCarbon.post_elec ?? null,
      baseline_gas_kwh: energyCarbon.baseline_gas ?? null,
      proposed_gas_kwh: energyCarbon.post_gas ?? null,
      carbon_reduction_tonnes: energyCarbon.carbon_reduction_tonnes ?? null,
      current_property_value: valuation.current_value ?? null,
      proposed_property_value_point_estimate: valuation.post_retrofit_value ?? null,
      value_impact_range_gbp: (valuation.indicative_range_low_value != null && valuation.indicative_range_high_value != null)
        ? [valuation.indicative_range_low_value, valuation.indicative_range_high_value]
        : null,
      value_impact_range_pct: (valuation.indicative_range_low_pct != null && valuation.indicative_range_high_pct != null)
        ? [valuation.indicative_range_low_pct, valuation.indicative_range_high_pct]
        : null,
      value_impact_disclaimer: valuation.disclaimer ?? null,
      assumptions: [
        "Property-value uplift is evaluated toward a fixed reference EPC band, not necessarily the exact band the selected retrofits would achieve.",
        "Carbon figures use the UK DESNZ 2024 factors (electricity 0.20705, gas 0.18254 kgCO2e/kWh).",
      ],
      limitations: limitations,
    };
  }

  // 5. POST /api/assessment
  async function runAssessment() {
    const payload = getInputs();
    try {
      const res = await fetch("/api/assessment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("API failed");
      const data = await res.json();

      applyCurrentScoreToUI(data.green_home_score);
      runWhatIfSimulation();
    } catch (err) {
      console.warn("Backend offline, loading local fallback data:", err);
      renderSubScores({
        epc_rating: 40,
        energy_intensity: 25,
        insulation: 20,
        heating: 40,
        glazing: 20,
        renewable_energy: 0,
        smart_controls: 0
      });
      localWhatIfMath();
    }
  }

  // 6. POST /api/what-if
  async function runWhatIfSimulation() {
    const inputs = getInputs();
    const payload = {
      ...inputs,
      selected_retrofits: Array.from(activeUpgrades).map(id => UPGRADE_TO_LEVER[id] || id)
    };

    try {
      const res = await fetch("/api/what-if", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("API failed");
      const data = await res.json();
      window.currentAssessmentData = buildAdvisorContext(data);
      applyPotentialScoreToUI(data.green_home_score.after);
      updateDashboardStats(data.energy_carbon, data.valuation);
    } catch (err) {
      localWhatIfMath();
    }
  }

  // Single source of truth for the carbon figure shown anywhere on the
  // page - Overview's metricCarbon and the Fuel Trade-Offs truth banner
  // both read from this one backend-computed value, so they can never
  // disagree the way a second, independently hand-written figure could.
  function formatCarbonTonnes(energyCarbon) {
    if (!energyCarbon || energyCarbon.carbon_reduction_kg == null) return "unavailable";
    return `${(energyCarbon.carbon_reduction_kg / 1000).toFixed(2)} tonnes/year`;
  }

  function updateDashboardStats(energyCarbon, valuation) {
    const dElec = Math.round((energyCarbon.elec_diff ?? 0) * 10) / 10;
    const dGas = Math.round((energyCarbon.gas_diff ?? 0) * 10) / 10;
    const carbonLabel = formatCarbonTonnes(energyCarbon);

    document.getElementById("metricElec").textContent = `${dElec > 0 ? '-' : '+'}${Math.abs(Math.round(dElec)).toLocaleString()} kWh/yr`;
    document.getElementById("metricGas").textContent = `${dGas >= 0 ? '-' : '+'}${Math.abs(Math.round(dGas)).toLocaleString()} kWh/yr`;

    const elecHintEl = document.getElementById("metricElecHint");
    if (elecHintEl) {
      elecHintEl.textContent = dElec < 0
        ? "Electricity use rises (e.g. heat pump demand)"
        : dElec > 0 ? "Electricity use falls for this scenario" : "No change for this scenario";
    }
    const gasHintEl = document.getElementById("metricGasHint");
    if (gasHintEl) {
      gasHintEl.textContent = dGas > 0
        ? "Gas use falls for this scenario"
        : dGas < 0 ? "Gas use rises for this scenario" : "No change for this scenario";
    }
    document.getElementById("metricCarbon").textContent =
      energyCarbon.carbon_reduction_kg != null ? `${(energyCarbon.carbon_reduction_kg / 1000).toFixed(2)} Tonnes/yr` : "—";

    const baseGas = parseFloat(document.getElementById("baselineGas").value) || 0;
    const afterGas = Math.max(0, Math.round((baseGas - dGas) * 10) / 10);

    const truthBannerText = document.getElementById("truthBannerText");
    if (truthBannerText) {
      const elecPhrase = dElec < 0
        ? `electricity use rises by ${Math.round(Math.abs(dElec)).toLocaleString()} kWh/yr`
        : dElec > 0
          ? `electricity use falls by ${Math.round(dElec).toLocaleString()} kWh/yr`
          : "electricity use is unchanged";
      const gasPhrase = afterGas === 0 && baseGas > 0
        ? "gas heating is eliminated for this scenario"
        : dGas > 0
          ? `gas use falls by ${Math.round(dGas).toLocaleString()} kWh/yr`
          : dGas < 0
            ? `gas use rises by ${Math.round(Math.abs(dGas)).toLocaleString()} kWh/yr`
            : "gas use is unchanged";
      const carbonPhrase = energyCarbon.carbon_reduction_kg != null
        ? (energyCarbon.carbon_reduction_kg >= 0
          ? `total carbon emissions fall by <strong>${carbonLabel}</strong>`
          : `total carbon emissions rise by <strong>${(Math.abs(energyCarbon.carbon_reduction_kg) / 1000).toFixed(2)} tonnes/year</strong>`)
        : "the carbon impact is unavailable for this scenario";
      truthBannerText.innerHTML =
        `<strong>The Net Result:</strong> In this scenario, ${elecPhrase} while ${gasPhrase}, so ${carbonPhrase} (DESNZ 2024 factors).`;
    }

    // Property value uplift: always the backend's real indicative range
    // (src/engines/valuation.py), never an invented percentage. The
    // backend evaluates uplift toward a fixed reference band (EPC "B"),
    // not a per-selected-retrofit prediction - see the metric-hint
    // caption below, which states that limitation rather than implying
    // the figure tracks whichever measures happen to be toggled.
    const baseline = valuation.current_value || parseFloat(document.getElementById("currentValue").value) || 0;
    const metricValueEl = document.getElementById("metricValue");
    const valueHintEl = document.getElementById("metricValueHint");

    if (!baseline || valuation.indicative_range_low_value == null || valuation.indicative_range_high_value == null) {
      metricValueEl.textContent = "Unavailable";
      if (valueHintEl) valueHintEl.textContent = "Property value or valuation model output unavailable.";
    } else {
      const deltaLow = valuation.indicative_range_low_value - baseline;
      const deltaHigh = valuation.indicative_range_high_value - baseline;
      metricValueEl.textContent =
        `+£${Math.round(deltaLow).toLocaleString()} – £${Math.round(deltaHigh).toLocaleString()}`;
      if (valueHintEl) {
        const lowPct = valuation.indicative_range_low_pct;
        const highPct = valuation.indicative_range_high_pct;
        const pctText = (typeof lowPct === "number" && typeof highPct === "number")
          ? ` (+${lowPct.toFixed(1)}% to +${highPct.toFixed(1)}%)`
          : "";
        valueHintEl.textContent = `Indicative modelled range toward a reference EPC band${pctText}`;
      }
    }

    const baseElec = parseFloat(document.getElementById("baselineElec").value) || 0;
    const afterElec = Math.max(0, Math.round((baseElec - dElec) * 10) / 10);

    document.getElementById("lblElecBefore").textContent = `${baseElec.toLocaleString()} kWh`;
    document.getElementById("lblElecAfter").textContent = `${afterElec.toLocaleString()} kWh`;
    document.getElementById("lblGasBefore").textContent = `${baseGas.toLocaleString()} kWh`;
    document.getElementById("lblGasAfter").textContent = `${afterGas.toLocaleString()} kWh (${afterGas === 0 ? "100% Clean" : "Reduced"})`;

    const maxFuel = Math.max(baseGas, baseElec, afterElec, 1);
    document.getElementById("barElecBefore").style.width = `${(baseElec / maxFuel) * 100}%`;
    document.getElementById("barElecAfter").style.width = `${(afterElec / maxFuel) * 100}%`;
    document.getElementById("barGasBefore").style.width = `${(baseGas / maxFuel) * 100}%`;
    document.getElementById("barGasAfter").style.width = `${(afterGas / maxFuel) * 100}%`;

    document.getElementById("tagElecChange").textContent = dElec < 0 ? `+${Math.round(Math.abs(dElec)).toLocaleString()} kWh clean power` : `-${Math.round(dElec).toLocaleString()} kWh saved`;
    document.getElementById("tagGasChange").textContent = afterGas === 0 ? "-100% Fossil fuel eliminated" : `-${Math.round(dGas).toLocaleString()} kWh gas reduced`;
  }

  // Degraded offline fallback ONLY - used when /api/what-if itself is
  // unreachable (see the catch in runWhatIfSimulation). This is a rough
  // client-side approximation, not the authoritative engine; it is
  // never used while the backend is reachable, and its boostPct-based
  // valuation guess is clearly an estimate, not a model output.
  function localWhatIfMath() {
    let dElec = 0;
    let dGas = 0;
    if (activeUpgrades.has("loft_insulation")) dGas += 1800;
    if (activeUpgrades.has("double_glazing")) dGas += 1200;
    if (activeUpgrades.has("smart_thermostat")) dGas += 840;
    if (activeUpgrades.has("heat_pump")) {
      dGas = 12000;
      dElec -= 2900;
    }
    if (activeUpgrades.has("solar_panels")) dElec += 1400;

    // DESNZ 2024 factors (kgCO2e/kWh) - same source of truth as
    // src/engines/carbon_energy.py, kept in sync manually since this
    // fallback path cannot reach the backend to compute it there.
    const ELEC_FACTOR = 0.20705;
    const GAS_FACTOR = 0.18254;

    const baseVal = parseFloat(document.getElementById("currentValue").value) || 350000;
    const boostPct = activeUpgrades.size * 0.015;
    updateDashboardStats(
      { elec_diff: dElec, gas_diff: dGas, carbon_reduction_kg: dElec * ELEC_FACTOR + dGas * GAS_FACTOR },
      {
        current_value: baseVal,
        indicative_range_low_value: baseVal * (1 + boostPct),
        indicative_range_high_value: baseVal * (1 + boostPct * 1.6)
      }
    );
  }

  // 7. Package Comparison (/api/plans/battle)
  document.getElementById("battleBudget").addEventListener("input", (e) => {
    document.getElementById("battleBudgetVal").textContent = `£${Number(e.target.value).toLocaleString()}`;
  });

  document.querySelectorAll(".obj-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".obj-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentObjective = btn.dataset.obj;
    });
  });

  function renderBattlePlans(data) {
    const grid = document.getElementById("battlePlansGrid");
    const planA = data.plans && data.plans.plan_a;
    const planB = data.plans && data.plans.plan_b;

    if (!planA || !planB) {
      grid.innerHTML = `<p class="battle-notice">${data.notice || "No feasible retrofit package fits that budget."}</p>`;
      return;
    }

    const currentScore = getCurrentScore();

    const renderCard = (plan, isWinner) => {
      const rawUplift = typeof plan.score_uplift === "number" ? plan.score_uplift : 0;
      const projectedScore = Math.min(100, Math.max(0, currentScore + rawUplift));
      const effectiveUplift = projectedScore - currentScore;
      return `
      <div class="battle-card ${isWinner ? "winning" : ""}">
        <div class="battle-card-top">
          <span class="plan-tag ${isWinner ? "highlight" : ""}">${isWinner ? "Plan B · Recommended" : "Plan A"}</span>
          <h3>${plan.title}</h3>
          <span class="plan-price">Est. Cost: £${Math.round(plan.total_estimated_cost).toLocaleString()}</span>
        </div>
        <ul class="plan-items">
          ${plan.included_measures.map(m => `<li><i data-lucide="check"></i> ${m}</li>`).join("")}
        </ul>
        <div class="plan-stats">
          <div><span>Score Uplift</span><strong>${effectiveUplift >= 0 ? "+" : ""}${effectiveUplift} pts (Score: ${projectedScore})</strong></div>
          <div><span>Projected EPC Uplift</span><strong>+${plan.projected_epc_uplift} pts</strong></div>
          <div><span>Package</span><strong>${plan.plan_id}</strong></div>
        </div>
      </div>
    `;
    };

    grid.innerHTML = renderCard(planA, false) + renderCard(planB, true);
    if (window.lucide) window.lucide.createIcons();
  }

  document.getElementById("btnRunBattle").addEventListener("click", async () => {
    const budget = Number(document.getElementById("battleBudget").value);
    const btn = document.getElementById("btnRunBattle");
    btn.innerHTML = '<i data-lucide="loader-2" class="spin"></i> Comparing...';
    btn.disabled = true;

    try {
      const res = await fetch("/api/plans/battle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...getInputs(),
          budget,
          objective: OBJECTIVE_TO_BACKEND[currentObjective] || "carbon"
        })
      });
      if (!res.ok) throw new Error("Package Comparison API failed");
      const data = await res.json();
      renderBattlePlans(data);
    } catch (err) {
      document.getElementById("battlePlansGrid").innerHTML =
        '<p class="battle-notice">Couldn\'t reach the comparison engine - please try again.</p>';
    } finally {
      setTimeout(() => {
        btn.innerHTML = '<i data-lucide="scale"></i> Compare Plans';
        btn.disabled = false;
        if (window.lucide) window.lucide.createIcons();
      }, 400);
    }
  });

  // 8. Grounded LLM Chatbot (/api/chat)
  (function injectChatStyles() {
    const style = document.createElement("style");
    style.textContent = `
      .chat-history-drawer { display: flex; flex-direction: column; gap: 10px; max-height: 420px; overflow-y: auto; margin-bottom: 12px; padding-right: 4px; }
      .chat-msg-user { align-self: flex-end; background: var(--sidebar-bg); color: #fff; padding: 10px 14px; border-radius: 14px 14px 2px 14px; max-width: 80%; font-size: 13px; }
      .chat-msg-bot p { margin: 0 0 6px 0; }
      .chat-msg-bot ul { margin: 0 0 6px 18px; padding: 0; }
      .chat-msg-bot.chat-error { color: #991b1b; }
      .chat-typing-dots { display: inline-flex; gap: 4px; align-items: center; }
      .chat-typing-dots span { width: 6px; height: 6px; border-radius: 50%; background: #9ca3af; animation: chatTypingBounce 1.2s infinite ease-in-out; }
      .chat-typing-dots span:nth-child(2) { animation-delay: 0.2s; }
      .chat-typing-dots span:nth-child(3) { animation-delay: 0.4s; }
      @keyframes chatTypingBounce { 0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); } 40% { opacity: 1; transform: scale(1); } }
    `;
    document.head.appendChild(style);
  })();

  function renderSimpleMarkdown(text) {
    const escaped = String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    const lines = escaped.split(/\r?\n/);
    let html = "";
    let inList = false;
    for (const line of lines) {
      const bullet = line.match(/^\s*[-*]\s+(.*)$/);
      if (bullet) {
        if (!inList) { html += "<ul>"; inList = true; }
        html += `<li>${bullet[1]}</li>`;
      } else {
        if (inList) { html += "</ul>"; inList = false; }
        if (line.trim() !== "") html += `<p>${line}</p>`;
      }
    }
    if (inList) html += "</ul>";
    return html;
  }

  function getChatHistoryDrawer() {
    let drawer = document.getElementById("chatHistoryDrawer");
    if (drawer) return drawer;

    const container = document.querySelector(".ai-box-inner");
    const chatBar = document.querySelector(".chat-bar");
    const welcomeBubble = document.querySelector(".ai-response-bubble");

    drawer = document.createElement("div");
    drawer.id = "chatHistoryDrawer";
    drawer.className = "chat-history-drawer";

    if (welcomeBubble) {
      drawer.appendChild(welcomeBubble);
    }
    container.insertBefore(drawer, chatBar);
    return drawer;
  }

  function appendChatBubble(role, innerHtml) {
    const drawer = getChatHistoryDrawer();
    const bubble = document.createElement("div");

    if (role === "user") {
      bubble.className = "chat-msg-user";
      bubble.innerHTML = innerHtml;
    } else {
      bubble.className = role === "error" ? "ai-response-bubble chat-msg-bot chat-error" : "ai-response-bubble chat-msg-bot";
      bubble.innerHTML = `<div class="ai-bot-avatar"><i data-lucide="${role === "error" ? "alert-triangle" : "bot"}"></i></div><div class="chat-msg-content">${innerHtml}</div>`;
    }

    drawer.appendChild(bubble);
    if (window.lucide) window.lucide.createIcons();
    drawer.scrollTop = drawer.scrollHeight;
    return bubble;
  }

  function showTypingIndicator() {
    return appendChatBubble(
      "bot",
      '<div class="chat-typing-dots"><span></span><span></span><span></span></div>'
    );
  }

  async function askAiAdvisor() {
    const input = document.getElementById("chatInputBox");
    const query = input.value.trim();
    if (!query) return;

    const btn = document.getElementById("btnChatSend");
    btn.textContent = "Verifying...";
    btn.disabled = true;
    input.disabled = true;

    appendChatBubble("user", `<p>${query.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>`);
    input.value = "";
    const typingBubble = showTypingIndicator();

    try {
      const payload = { user_question: query };
      if (window.currentCustomerId) payload.customer_id = window.currentCustomerId;
      if (window.currentAssessmentData && Object.keys(window.currentAssessmentData).length) {
        payload.property_data = window.currentAssessmentData;
      }

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const status = res.status;
        typingBubble.remove();
        const message = status === 429
          ? "The AI advisor has hit its usage quota right now. Please try again in a little while."
          : "The AI advisor couldn't process that request (server error). Please try again.";
        appendChatBubble("error", `<p>${message}</p>`);
        return;
      }

      const data = await res.json();
      typingBubble.remove();
      appendChatBubble("bot", renderSimpleMarkdown(data.reply || "(No reply received.)"));
    } catch (err) {
      typingBubble.remove();
      appendChatBubble(
        "error",
        "<p>Couldn't reach the AI advisor - check your connection and try again.</p>"
      );
    } finally {
      btn.innerHTML = 'Ask Advisor <i data-lucide="arrow-right"></i>';
      btn.disabled = false;
      input.disabled = false;
      if (window.lucide) window.lucide.createIcons();
    }
  }

  document.getElementById("btnChatSend").addEventListener("click", askAiAdvisor);
  document.getElementById("chatInputBox").addEventListener("keydown", (e) => {
    if (e.key === "Enter") askAiAdvisor();
  });

  // 8b. AI Advisor Expand / Full-Screen Toggle
  const advisorCard = document.getElementById("advisorCard");
  const advisorExpandBtn = document.getElementById("advisorExpandBtn");

  function setAdvisorFullscreen(isFullscreen) {
    if (!advisorCard || !advisorExpandBtn) return;
    advisorCard.classList.toggle("advisor-fullscreen", isFullscreen);
    advisorExpandBtn.innerHTML = isFullscreen ? "✕ Close" : "⛶ Expand";
    advisorExpandBtn.title = isFullscreen ? "Minimize" : "Expand to Full Screen";

    if (isFullscreen) {
      const drawer = document.getElementById("chatHistoryDrawer");
      if (drawer) drawer.scrollTop = drawer.scrollHeight;
      const input = document.getElementById("chatInputBox");
      if (input) input.focus();
    }
  }

  if (advisorExpandBtn) {
    advisorExpandBtn.addEventListener("click", () => {
      setAdvisorFullscreen(!advisorCard.classList.contains("advisor-fullscreen"));
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && advisorCard && advisorCard.classList.contains("advisor-fullscreen")) {
      setAdvisorFullscreen(false);
    }
  });

  // 9. Form Handlers
  document.getElementById("assessmentForm").addEventListener("submit", (e) => {
    e.preventDefault();
    runAssessment();
  });

  // Active Nav Scroll Spy
  const sections = document.querySelectorAll("section[id]");
  window.addEventListener("scroll", () => {
    const scrollY = window.pageYOffset;

    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 80) {
      document.querySelectorAll(".side-nav a").forEach(a => a.classList.remove("active"));
      const lastLink = document.querySelector(".side-nav a:last-child");
      if (lastLink) lastLink.classList.add("active");
      return;
    }

    sections.forEach(current => {
      const sectionHeight = current.offsetHeight;
      const sectionTop = current.offsetTop - 120;
      const sectionId = current.getAttribute("id");
      if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
        document.querySelectorAll(".side-nav a").forEach(a => a.classList.remove("active"));
        const activeLink = document.querySelector(`.side-nav a[href*=${sectionId}]`);
        if (activeLink) activeLink.classList.add("active");
      }
    });
  });

  renderUpgrades();
  runAssessment();
});