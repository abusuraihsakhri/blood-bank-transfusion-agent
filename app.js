"use strict";

const state = { pyodide: null, ready: false, lastResult: null };
const runtimeStatus = document.getElementById("runtimeStatus");
const resultTitle = document.getElementById("resultTitle");
const resultSummary = document.getElementById("resultSummary");
const resultJson = document.getElementById("resultJson");
const copyResult = document.getElementById("copyResult");

function setRuntimeStatus(message, kind = "loading") {
  runtimeStatus.textContent = message;
  runtimeStatus.classList.toggle("is-ready", kind === "ready");
  runtimeStatus.classList.toggle("is-error", kind === "error");
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("bb-theme", theme);
}

const savedTheme = localStorage.getItem("bb-theme");
if (savedTheme === "dark" || savedTheme === "light") {
  setTheme(savedTheme);
} else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
  setTheme("dark");
}

document.getElementById("themeToggle").addEventListener("click", () => {
  setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});

for (const tab of document.querySelectorAll(".tab")) {
  tab.addEventListener("click", () => {
    const tool = tab.dataset.tool;
    document.querySelectorAll(".tab").forEach((el) => el.classList.toggle("is-active", el === tab));
    document.querySelectorAll(".tool-form").forEach((el) => el.classList.toggle("is-active", el.dataset.panel === tool));
  });
}

function csvList(value) {
  return String(value || "").split(/[;,]/).map((item) => item.trim()).filter(Boolean);
}

function parseAntigens(value) {
  const output = {};
  for (const item of csvList(value)) {
    const idx = item.indexOf(":");
    if (idx > 0) output[item.slice(0, idx).trim()] = item.slice(idx + 1).trim();
  }
  return output;
}

function formObject(form) {
  const data = new FormData(form);
  return Object.fromEntries(data.entries());
}

async function callPython(action, payload) {
  if (!state.ready || !state.pyodide) throw new Error("Python runtime is not ready yet.");
  state.pyodide.globals.set("action_json", JSON.stringify({ action, payload }));
  const output = await state.pyodide.runPythonAsync(`
import json
request = json.loads(action_json)
action = request["action"]
p = request["payload"]

if action == "crossmatch":
    patient = PatientProfile(
        patient_id="BROWSER-PATIENT",
        name="Browser case",
        abo_rh=p["patient_abo"],
        identified_antibodies=p.get("antibodies", []),
        special_requirements=p.get("special_requirements", []),
    )
    unit = BloodUnit(
        unit_id="BROWSER-UNIT",
        product_type=BloodProductType(p["product_type"]),
        abo_rh=p["donor_abo"],
        antigen_phenotype=p.get("donor_antigens", {}),
        is_irradiated=bool(p.get("unit_irradiated")),
        is_cmv_negative=bool(p.get("unit_cmv")),
        is_washed=bool(p.get("unit_washed")),
        is_quarantined=bool(p.get("quarantined")),
    )
    result = CrossmatchEngine.crossmatch_unit(patient, unit)
elif action == "donor":
    result = CrossmatchEngine.calculate_compatible_donor_frequency(p["patient_abo"], p.get("antibodies", []))
elif action == "mtp":
    tracker = MTPTracker(
        event_id="BROWSER-MTP",
        patient_id="BROWSER-PATIENT",
        issued_prbc=int(p["prbc"]),
        issued_ffp=int(p["ffp"]),
        issued_platelets=int(p["platelets"]),
        issued_cryo_pools=int(p["cryo"]),
    )
    result = tracker.get_status()
elif action == "coldchain":
    monitor = ColdChainMonitor(BloodProductType(p["product_type"]))
    for item in p["readings"]:
        monitor.record_reading(TempReading(float(item[0]), float(item[1]), "browser-sensor"))
    result = monitor.evaluate_compliance()
elif action == "reaction":
    result = TransfusionSafetyManager.adjudicate_reaction(
        temp_rise_c=float(p["temp_rise"]),
        onset_minutes=int(p["onset_minutes"]),
        hypotension=bool(p.get("hypotension")),
        dyspnea=bool(p.get("dyspnea")),
        hemoglobinuria=bool(p.get("hemoglobinuria")),
        urticaria=bool(p.get("urticaria")),
        wheezing_or_stridor=bool(p.get("wheezing")),
        dat_positive=bool(p.get("dat_positive")),
        bacterial_gram_positive=bool(p.get("gram_positive")),
        jvd_or_fluid_overload=bool(p.get("fluid_overload")),
    )
else:
    raise ValueError(f"Unknown action: {action}")

json.dumps(result)
`);
  return JSON.parse(output);
}

function renderResult(title, result) {
  state.lastResult = result;
  resultTitle.textContent = title;
  resultJson.textContent = JSON.stringify(result, null, 2);
  copyResult.disabled = false;

  let summary = "Analysis completed.";
  if (Object.hasOwn(result, "compatible")) {
    summary = result.compatible
      ? "Compatible under the modelled rules. Review component policy and all patient-specific requirements before issue."
      : `Not compatible under the modelled rules. ${(result.reasons_incompatible || result.reasons || []).join(" ")}`;
  } else if (Object.hasOwn(result, "overall_compatible_donor_percentage")) {
    summary = `${result.overall_compatible_donor_percentage}% estimated compatible. Approximately 1 in ${result.estimated_units_to_screen_for_one_compatible} randomly selected units under the model assumptions.`;
  } else if (Object.hasOwn(result, "ratio_compliance_pct")) {
    summary = `${result.ratio_compliance_pct}% modelled ratio compliance. ${result.coagulopathy_risk_status}. ${result.recommendation}`;
  } else if (Object.hasOwn(result, "quarantine_required")) {
    summary = `${result.quarantine_required ? "Quarantine flag triggered." : "No quarantine flag triggered."} ${result.cumulative_out_of_storage_minutes} minutes outside the configured range.`;
  } else if (Object.hasOwn(result, "adjudicated_reaction")) {
    summary = `${result.adjudicated_reaction} — ${result.severity_grade}. This is a rule-based classification, not a diagnostic determination.`;
  }
  resultSummary.textContent = summary;
}

async function handleSubmit(form, action, buildPayload, title) {
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    const payload = buildPayload(form);
    const result = await callPython(action, payload);
    renderResult(title, result);
  } catch (error) {
    resultTitle.textContent = "Could not run analysis";
    resultSummary.textContent = `Error: ${String(error.message || error)}`;
    resultJson.textContent = "{}";
  } finally {
    button.disabled = false;
  }
}

const crossmatchForm = document.getElementById("crossmatchForm");
crossmatchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  handleSubmit(crossmatchForm, "crossmatch", (form) => {
    const v = formObject(form);
    const requirements = [];
    if (v.req_irradiated) requirements.push("Irradiated");
    if (v.req_cmv) requirements.push("CMV-Negative");
    if (v.req_washed) requirements.push("Washed");
    return {
      patient_abo: v.patient_abo,
      donor_abo: v.donor_abo,
      product_type: v.product_type,
      antibodies: csvList(v.antibodies),
      donor_antigens: parseAntigens(v.donor_antigens),
      special_requirements: requirements,
      unit_irradiated: Boolean(v.unit_irradiated),
      unit_cmv: Boolean(v.unit_cmv),
      unit_washed: Boolean(v.unit_washed),
      quarantined: Boolean(v.quarantined),
    };
  }, "Crossmatch result");
});

const donorForm = document.getElementById("donorForm");
donorForm.addEventListener("submit", (event) => {
  event.preventDefault();
  handleSubmit(donorForm, "donor", (form) => {
    const v = formObject(form);
    return { patient_abo: v.patient_abo, antibodies: csvList(v.antibodies) };
  }, "Donor-frequency estimate");
});

const mtpForm = document.getElementById("mtpForm");
mtpForm.addEventListener("submit", (event) => {
  event.preventDefault();
  handleSubmit(mtpForm, "mtp", (form) => formObject(form), "MTP ratio result");
});

const coldchainForm = document.getElementById("coldchainForm");
coldchainForm.addEventListener("submit", (event) => {
  event.preventDefault();
  handleSubmit(coldchainForm, "coldchain", (form) => {
    const v = formObject(form);
    const readings = csvList(v.log_stream).map((entry) => {
      const [time, temp] = entry.split(":", 2).map(Number);
      if (!Number.isFinite(time) || !Number.isFinite(temp)) throw new Error(`Invalid reading: ${entry}`);
      return [time, temp];
    });
    if (!readings.length) throw new Error("Enter at least one time:temperature reading.");
    return { product_type: v.product_type, readings };
  }, "Cold-chain result");
});

const reactionForm = document.getElementById("reactionForm");
reactionForm.addEventListener("submit", (event) => {
  event.preventDefault();
  handleSubmit(reactionForm, "reaction", (form) => {
    const v = formObject(form);
    return {
      temp_rise: v.temp_rise,
      onset_minutes: v.onset_minutes,
      hypotension: Boolean(v.hypotension),
      dyspnea: Boolean(v.dyspnea),
      hemoglobinuria: Boolean(v.hemoglobinuria),
      urticaria: Boolean(v.urticaria),
      wheezing: Boolean(v.wheezing),
      dat_positive: Boolean(v.dat_positive),
      gram_positive: Boolean(v.gram_positive),
      fluid_overload: Boolean(v.fluid_overload),
    };
  }, "Reaction-triage result");
});

copyResult.addEventListener("click", async () => {
  if (!state.lastResult) return;
  await navigator.clipboard.writeText(JSON.stringify(state.lastResult, null, 2));
  const previous = copyResult.textContent;
  copyResult.textContent = "Copied";
  setTimeout(() => { copyResult.textContent = previous; }, 900);
});

async function initializePython() {
  setRuntimeStatus("Loading Python…");
  try {
    if (typeof loadPyodide !== "function") throw new Error("Pyodide loader was not available from the CDN.");
    state.pyodide = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/" });
    const response = await fetch("blood_bank_transfusion.py", { cache: "no-cache" });
    if (!response.ok) throw new Error(`Could not load Python model (${response.status}).`);
    const source = await response.text();
    await state.pyodide.runPythonAsync(source);
    state.ready = true;
    setRuntimeStatus("Python ready", "ready");
  } catch (error) {
    console.error(error);
    state.ready = false;
    setRuntimeStatus("Runtime unavailable", "error");
    resultTitle.textContent = "Python runtime unavailable";
    resultSummary.textContent = "The page loaded, but the browser Python runtime could not start. Check network access to jsDelivr and reload.";
  }
}

window.addEventListener("DOMContentLoaded", initializePython);
