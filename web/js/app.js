/** Main UI: tabs, worker bridge, Play / Compare / Results / Rules / Help. */

import { createMenu, createCompareMenu } from "./menu.js";
import { createControls, bindManualKeys } from "./controls.js";
import { drawBoard, agentAtEvent } from "./renderer.js";
import { renderBarChart, fillResultsTable } from "./charts.js";
import { renderHelpTab, renderRulesTab } from "./help.js";

const loadingEl = document.getElementById("loading");
const loadingMsg = document.getElementById("loading-msg");
const retryBtn = document.getElementById("retry-btn");
const shellEl = document.getElementById("shell");
const errorBanner = document.getElementById("error-banner");
const canvas = document.getElementById("board");

let worker = null;
let reqId = 0;
const pending = new Map();
let helpData = { settings: {}, agents: {}, sections: {} };
let options = { maps: [], agents: [], heuristics: [] };

let mapInfo = null;
let state = null;
let agentsMeta = [];
let historyEvents = [];
let selectedId = null;
let visionOn = false;
let beliefOn = false;
let visibleCells = null;
let beliefCells = null;
let playing = false;
let playTimer = null;
let pendingConfig = null;
let waitingManual = false;
let anim = null;

const menuRoot = document.getElementById("play-menu");
const controlsRoot = document.getElementById("play-controls");
const compareMenuRoot = document.getElementById("compare-menu");
let menuApi = null;
let controlsApi = null;
let compareApi = null;

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}
function clearError() {
  errorBanner.classList.add("hidden");
  errorBanner.textContent = "";
}
function setLoading(message) {
  loadingMsg.textContent = message;
}

function callWorker(fn, args = []) {
  const id = ++reqId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, fn, args });
  });
}

function onWorkerMessage(event) {
  const data = event.data || {};
  if (data.type === "progress") {
    setLoading(data.message);
    return;
  }
  if (data.type === "ready") {
    loadingEl.classList.add("hidden");
    shellEl.classList.remove("hidden");
    clearError();
    bootstrap();
    return;
  }
  if (data.type === "init_error") {
    setLoading(`Failed to load: ${data.error}`);
    retryBtn.classList.remove("hidden");
    showError(`${data.error} — Run python tools/build_web.py then serve the web/ folder.`);
    return;
  }
  const wait = pending.get(data.id);
  if (!wait) return;
  pending.delete(data.id);
  if (data.error) wait.reject(new Error(data.error));
  else wait.resolve(data.result);
}

function startWorker() {
  if (worker) worker.terminate();
  pending.clear();
  loadingEl.classList.remove("hidden");
  shellEl.classList.add("hidden");
  retryBtn.classList.add("hidden");
  setLoading("Starting worker…");
  worker = new Worker("./js/worker.js");
  worker.onmessage = onWorkerMessage;
  worker.onerror = (err) => {
    setLoading(`Worker error: ${err.message}`);
    retryBtn.classList.remove("hidden");
    showError(err.message);
  };
  worker.postMessage({ type: "init" });
}

function switchTab(name) {
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
    b.setAttribute("aria-selected", b.dataset.tab === name ? "true" : "false");
  });
  document.querySelectorAll(".tab-panel").forEach((p) => {
    p.classList.toggle("hidden", p.id !== `tab-${name}`);
  });
}

function describeEvent(event) {
  const who = `Agent #${event.agent_id}`;
  if (event.event_type === "infect") {
    return `${who} infected ${(event.newly_infected || []).map((id) => `#${id}`).join(", ")}`;
  }
  if (event.event_type === "heal") return `${who} healed #${event.healed_id}`;
  if (event.event_type === "illegal") return `${who} illegal → STAY`;
  return `${who} ${event.event_type} (${event.action})`;
}

function pushLog(text) {
  const ul = document.getElementById("event-log");
  const li = document.createElement("li");
  li.textContent = text;
  ul.prepend(li);
}

function currentAgent() {
  if (!state || state.done) return null;
  return state.agents[state.current_index] || null;
}

function currentAiName() {
  const a = currentAgent();
  if (!a) return null;
  const meta = agentsMeta.find((m) => m.id === a.id);
  return meta ? meta.ai : null;
}

function isManualTurn() {
  return !!(state && !state.done && currentAiName() === "manual");
}

function updateHud() {
  const hud = document.getElementById("hud");
  if (!state) {
    hud.innerHTML = "<p>Configure the left panel and press Start.</p>";
    return;
  }
  const counts = { zombie: 0, human: 0, healer: 0 };
  for (const a of state.agents) counts[a.role] = (counts[a.role] || 0) + 1;
  const acting = currentAgent();
  const meta = agentsMeta.map((m) => `${m.role}: ${m.ai}`).join(" · ");
  let statsHtml = "";
  if (selectedId != null) {
    const last = [...historyEvents].reverse().find((e) => e.agent_id === selectedId);
    if (last && last.stats) {
      const s = last.stats;
      statsHtml = `<p class="stats">Selected #${selectedId} last move: nodes ${s.nodes_expanded ?? "—"}, time ${(s.time_seconds ?? 0).toFixed?.(4) ?? s.time_seconds}</p>`;
    }
  }
  hud.innerHTML = `
    <p><strong>Round</strong> ${state.round_number} / ${state.max_rounds}</p>
    <p><strong>Counts</strong> Z ${counts.zombie} · H ${counts.human} · + ${counts.healer}</p>
    <p><strong>Infections</strong> ${state.infections} · <strong>Heals</strong> ${state.heals}</p>
    <p><strong>AI</strong> ${meta}</p>
    <p><strong>Acting</strong> ${acting ? `#${acting.id} (${acting.role})` : "—"} ${isManualTurn() ? "· MANUAL" : ""}</p>
    ${statsHtml}
  `;
}

async function refreshOverlays() {
  visibleCells = null;
  beliefCells = null;
  if (!state || selectedId == null) return;
  try {
    if (visionOn) {
      const obs = await callWorker("get_observation", [selectedId]);
      visibleCells = obs.visible_cells;
    }
    if (beliefOn) {
      const bel = await callWorker("get_belief_map", [selectedId]);
      beliefCells = bel.cells;
    }
  } catch (_) {
    /* ignore overlay errors */
  }
}

async function render() {
  await refreshOverlays();
  drawBoard(canvas, mapInfo, state, {
    selectedId,
    visibleCells: visionOn ? visibleCells : null,
    beliefCells: beliefOn ? beliefCells : null,
    anim,
  });
  updateHud();
  const end = document.getElementById("end-overlay");
  if (state && state.done) {
    end.classList.remove("hidden");
    document.getElementById("end-title").textContent =
      state.winner === "zombies" ? "Zombies win" : "Humans win";
    document.getElementById("end-detail").textContent =
      `${state.reason} · rounds ${state.round_number} · infections ${state.infections} · heals ${state.heals}`;
    stopPlay();
  } else {
    end.classList.add("hidden");
  }
  controlsApi?.setEnabled(!!state && !state.done);
  waitingManual = isManualTurn();
  if (waitingManual) {
    stopPlay();
    document.getElementById("manual-hint").classList.remove("hidden");
  } else {
    document.getElementById("manual-hint").classList.add("hidden");
  }
}

function stopPlay() {
  playing = false;
  clearInterval(playTimer);
  playTimer = null;
  controlsApi?.setPlaying(false);
}

async function startGame(config) {
  clearError();
  stopPlay();
  pendingConfig = config;
  historyEvents = [];
  document.getElementById("event-log").innerHTML = "";
  try {
    const result = await callWorker("new_game", [config]);
    mapInfo = result.map;
    state = result.state;
    agentsMeta = result.agents || [];
    selectedId = state.agents[0]?.id ?? null;
    pushLog("Game started.");
    await render();
  } catch (err) {
    showError(String(err.message || err));
  }
}

async function stepOnce() {
  if (!state || state.done) return;
  if (isManualTurn()) {
    controlsApi.toast("Manual turn — use keyboard");
    return;
  }
  clearError();
  try {
    const result = await callWorker("step", []);
    applyStepResult(result);
  } catch (err) {
    showError(String(err.message || err));
    stopPlay();
  }
}

function applyStepResult(result) {
  state = result.state;
  if (result.event) {
    historyEvents.push(result.event);
    pushLog(describeEvent(result.event));
    if (result.event.event_type === "infect" && result.event.newly_infected?.length) {
      anim = { id: result.event.newly_infected[0], kind: "infect" };
      setTimeout(() => { anim = null; render(); }, 280);
    }
    if (result.event.event_type === "heal") {
      anim = { id: result.event.healed_id, kind: "heal" };
      setTimeout(() => { anim = null; render(); }, 280);
    }
  }
  render();
}

async function stepRound() {
  if (!state || state.done) return;
  if (isManualTurn()) {
    controlsApi.toast("Manual turn — use keyboard");
    return;
  }
  clearError();
  try {
    const result = await callWorker("play_round", []);
    state = result.state;
    for (const event of result.events || []) {
      historyEvents.push(event);
      pushLog(describeEvent(event));
    }
    await render();
  } catch (err) {
    showError(String(err.message || err));
  }
}

function togglePlay() {
  if (!state || state.done) return;
  if (isManualTurn()) {
    controlsApi.toast("Paused for manual input");
    return;
  }
  playing = !playing;
  controlsApi.setPlaying(playing);
  if (!playing) {
    clearInterval(playTimer);
    playTimer = null;
    return;
  }
  const ms = Math.max(50, 1000 / (controlsApi.getSpeed() || 5));
  playTimer = setInterval(() => {
    if (isManualTurn() || (state && state.done)) {
      stopPlay();
      render();
      return;
    }
    stepOnce();
  }, ms);
}

async function submitManual(action) {
  if (!isManualTurn()) return;
  clearError();
  try {
    const result = await callWorker("submit_manual_action", [action]);
    applyStepResult(result);
  } catch (err) {
    controlsApi.toast("can't move there");
    showError(String(err.message || err));
  }
}

async function runCompare(cfg) {
  clearError();
  compareApi.setBusy(true);
  try {
    const result = await callWorker("run_compare", [
      {
        map: cfg.map,
        seed: cfg.seed,
        max_rounds: 40,
        zombie_ai: "rulebased",
        human_ai: "rulebased",
        healer_ai: "rulebased",
        search_depth: 2,
        move_time_limit: 0.2,
        _compare_role: cfg.role,
      },
      cfg.agents,
      cfg.n_games,
    ]);
    showCompare(result.rows);
  } catch (err) {
    showError(String(err.message || err));
  } finally {
    compareApi.setBusy(false);
  }
}

function showCompare(rows) {
  const table = document.getElementById("compare-table");
  fillResultsTable(table, rows);
  renderBarChart(document.getElementById("chart-win"), rows, "win_rate", "Win rate");
  renderBarChart(document.getElementById("chart-nodes"), rows, "avg_nodes_expanded", "Avg nodes expanded");
  document.getElementById("chart-win-cap").textContent =
    "Higher bars mean that AI won more often as the varied role (zombies by default).";
  document.getElementById("chart-nodes-cap").textContent =
    "Log scale: lower usually means cheaper decisions (fewer search expansions).";
}

async function loadResultsTab() {
  const root = document.getElementById("results-body");
  root.innerHTML = "";
  try {
    const resp = await fetch("./data/results/index.json");
    if (!resp.ok) {
      root.innerHTML = `<p class="muted">No exported results yet. Run experiments locally, then <code>python tools/export_results.py</code>.</p>`;
      return;
    }
    const index = await resp.json();
    const items = index.items || [];
    if (!items.length) {
      root.innerHTML = `<p class="muted">No exported results yet. Run experiments locally, then <code>python tools/export_results.py</code>.</p>`;
      return;
    }
    for (const item of items) {
      const card = document.createElement("article");
      card.className = "result-card";
      card.innerHTML = `<h3>${item.title}</h3><p>${item.description || ""}</p>`;
      if (item.image) {
        const img = document.createElement("img");
        img.src = item.image;
        img.alt = item.title;
        card.appendChild(img);
      }
      if (item.json) {
        try {
          const data = await (await fetch(item.json)).json();
          const table = document.createElement("table");
          table.className = "results-table";
          fillResultsTable(table, data.rows || []);
          card.appendChild(table);
          const canvas = document.createElement("canvas");
          canvas.width = 640;
          canvas.height = 280;
          card.appendChild(canvas);
          renderBarChart(canvas, data.rows || [], "win_rate", `${item.title} — win rate`);
        } catch (_) {
          /* skip broken export */
        }
      }
      root.appendChild(card);
    }
  } catch (_) {
    root.innerHTML = `<p class="muted">Could not load <code>data/results/index.json</code>.</p>`;
  }
}

async function bootstrap() {
  helpData = await (await fetch("./data/help.json")).json();
  options = await callWorker("list_options", []);
  menuApi = createMenu(menuRoot, helpData, options);
  menuApi.onStart((cfg) => startGame(cfg));
  controlsApi = createControls(controlsRoot, {
    onStart: () => {
      if (menuApi.validate()) startGame(menuApi.readConfig());
    },
    onPlayToggle: togglePlay,
    onStep: stepOnce,
    onRound: stepRound,
    onSpeed: () => {
      if (playing) {
        stopPlay();
        togglePlay();
      }
    },
    onVision: async (on) => { visionOn = on; await render(); },
    onBelief: async (on) => { beliefOn = on; await render(); },
    onReplay: () => {
      const blob = new Blob([JSON.stringify({ events: historyEvents, final: state }, null, 2)], {
        type: "application/json",
      });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "replay.json";
      a.click();
    },
  });
  controlsApi.bindInfo(helpData.settings);

  compareApi = createCompareMenu(compareMenuRoot, helpData, options);
  compareApi.onRun(runCompare);

  renderHelpTab(document.getElementById("help-root"), helpData);
  renderRulesTab(document.getElementById("rules-root"));
  loadResultsTab();

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
  document.getElementById("end-again").addEventListener("click", () => {
    if (pendingConfig) startGame(pendingConfig);
  });
  document.getElementById("end-settings").addEventListener("click", () => {
    document.getElementById("end-overlay").classList.add("hidden");
    switchTab("play");
  });

  canvas.addEventListener("click", async (e) => {
    const hit = agentAtEvent(e, canvas, mapInfo, state);
    if (hit) {
      selectedId = hit.id;
      await render();
    }
  });

  bindManualKeys(
    (action) => submitManual(action),
    () => isManualTurn(),
  );
  window.addEventListener("resize", () => render());
  switchTab("play");
}

retryBtn.addEventListener("click", startWorker);
startWorker();
