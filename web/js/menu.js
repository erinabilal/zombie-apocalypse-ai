/** Setup panel: settings form, validation, defaults, info icons. */

const AI_OPTIONS = [
  "manual", "random", "rulebased", "bfs", "dfs", "ucs", "greedy", "astar",
  "minimax", "alphabeta", "expectimax", "qlearning",
];

const DEFAULTS = {
  map: "small",
  n_zombies: 1,
  n_humans: 4,
  n_healers: 1,
  max_rounds: 60,
  heal_cooldown: 3,
  seed: 0,
  vision_radius: null,
  hidden_roles: false,
  search_depth: 2,
  zombie_ai: "rulebased",
  human_ai: "rulebased",
  healer_ai: "rulebased",
  heuristic: "manhattan",
};

/**
 * Build the Play-tab setup panel into root and return accessors.
 * @param {HTMLElement} root
 * @param {object} helpData
 * @param {{maps:string[], agents:string[], heuristics:string[]}} options
 */
export function createMenu(root, helpData, options) {
  const agents = (options.agents || AI_OPTIONS).filter((a) => a !== "qlearning" || true);
  root.innerHTML = `
    <h2>Setup</h2>
    <div class="field" data-key="map"><label>Map <button type="button" class="info" aria-label="About map">i</button></label>
      <select id="cfg-map"></select></div>
    <div class="field" data-key="n_zombies"><label>Zombies <button type="button" class="info">i</button></label>
      <input id="cfg-zombies" type="number" min="1" value="1" /></div>
    <div class="field" data-key="n_humans"><label>Humans <button type="button" class="info">i</button></label>
      <input id="cfg-humans" type="number" min="0" value="4" /></div>
    <div class="field" data-key="n_healers"><label>Healers <button type="button" class="info">i</button></label>
      <input id="cfg-healers" type="number" min="0" value="1" /></div>
    <div class="field" data-key="max_rounds"><label>Rounds <button type="button" class="info">i</button></label>
      <input id="cfg-rounds" type="number" min="1" value="60" /></div>
    <div class="field" data-key="heal_cooldown"><label>Heal cooldown <button type="button" class="info">i</button></label>
      <input id="cfg-cooldown" type="number" min="1" value="3" /></div>
    <div class="field" data-key="seed"><label>Seed <button type="button" class="info">i</button></label>
      <div class="row"><input id="cfg-seed" type="number" value="0" />
      <button type="button" id="cfg-seed-rand" class="secondary">Random</button></div></div>
    <div class="field" data-key="vision_radius"><label>Vision radius <button type="button" class="info">i</button></label>
      <div class="row"><input id="cfg-vision" type="range" min="0" max="12" value="0" />
      <span id="cfg-vision-label">Off</span></div></div>
    <div class="field" data-key="hidden_roles"><label class="check"><input id="cfg-hidden" type="checkbox" /> Hidden roles
      <button type="button" class="info">i</button></label></div>
    <div class="field" data-key="search_depth"><label>Search depth <button type="button" class="info">i</button></label>
      <input id="cfg-depth" type="number" min="1" max="3" value="2" /></div>
    <div class="field" data-key="zombie_ai"><label>Zombie AI <button type="button" class="info">i</button></label>
      <select id="cfg-zombie-ai"></select></div>
    <div class="field" data-key="human_ai"><label>Human AI <button type="button" class="info">i</button></label>
      <select id="cfg-human-ai"></select></div>
    <div class="field" data-key="healer_ai"><label>Healer AI <button type="button" class="info">i</button></label>
      <select id="cfg-healer-ai"></select></div>
    <div class="field hidden" data-key="heuristic" id="heuristic-field"><label>Heuristic <button type="button" class="info">i</button></label>
      <select id="cfg-heuristic"></select></div>
    <p id="cfg-error" class="form-error hidden"></p>
    <button type="button" id="cfg-start" class="primary">Start</button>
    <button type="button" id="cfg-reset" class="secondary">Reset to defaults</button>
    <div id="tip-pop" class="tip-pop hidden" role="tooltip"></div>
  `;

  const mapSel = root.querySelector("#cfg-map");
  for (const m of options.maps || ["small", "medium", "large"]) {
    const o = document.createElement("option");
    o.value = m; o.textContent = m; mapSel.appendChild(o);
  }
  for (const [id, list] of [
    ["#cfg-zombie-ai", agents],
    ["#cfg-human-ai", agents],
    ["#cfg-healer-ai", agents],
  ]) {
    const sel = root.querySelector(id);
    for (const a of list) {
      const o = document.createElement("option");
      o.value = a; o.textContent = a; sel.appendChild(o);
    }
  }
  const heur = root.querySelector("#cfg-heuristic");
  for (const h of options.heuristics || ["manhattan", "euclidean", "maze"]) {
    const o = document.createElement("option");
    o.value = h; o.textContent = h; heur.appendChild(o);
  }

  const tip = root.querySelector("#tip-pop");
  root.querySelectorAll(".field").forEach((field) => {
    const key = field.dataset.key;
    const btn = field.querySelector(".info");
    if (!btn) return;
    const show = () => {
      const entry = helpData.settings && helpData.settings[key];
      tip.textContent = typeof entry === "string" ? entry : (entry?.summary || "");
      tip.classList.remove("hidden");
      const r = btn.getBoundingClientRect();
      tip.style.left = `${Math.min(window.innerWidth - 280, r.left)}px`;
      tip.style.top = `${r.bottom + 6}px`;
    };
    btn.addEventListener("mouseenter", show);
    btn.addEventListener("focus", show);
    btn.addEventListener("click", show);
    btn.addEventListener("mouseleave", () => tip.classList.add("hidden"));
    btn.addEventListener("blur", () => tip.classList.add("hidden"));
  });

  const vision = root.querySelector("#cfg-vision");
  const visionLabel = root.querySelector("#cfg-vision-label");
  const syncVision = () => {
    const v = Number(vision.value);
    visionLabel.textContent = v === 0 ? "Off" : String(v);
  };
  vision.addEventListener("input", syncVision);

  const syncHeuristic = () => {
    const need = ["greedy", "astar"].includes(root.querySelector("#cfg-zombie-ai").value)
      || ["greedy", "astar"].includes(root.querySelector("#cfg-human-ai").value)
      || ["greedy", "astar"].includes(root.querySelector("#cfg-healer-ai").value);
    root.querySelector("#heuristic-field").classList.toggle("hidden", !need);
  };
  root.querySelectorAll("#cfg-zombie-ai, #cfg-human-ai, #cfg-healer-ai").forEach((el) => {
    el.addEventListener("change", syncHeuristic);
  });

  function readConfig() {
    const v = Number(vision.value);
    return {
      map: mapSel.value,
      n_zombies: Number(root.querySelector("#cfg-zombies").value),
      n_humans: Number(root.querySelector("#cfg-humans").value),
      n_healers: Number(root.querySelector("#cfg-healers").value),
      max_rounds: Number(root.querySelector("#cfg-rounds").value),
      heal_cooldown: Number(root.querySelector("#cfg-cooldown").value),
      seed: Number(root.querySelector("#cfg-seed").value),
      vision_radius: v === 0 ? null : v,
      hidden_roles: root.querySelector("#cfg-hidden").checked,
      search_depth: Math.min(3, Math.max(1, Number(root.querySelector("#cfg-depth").value) || 2)),
      zombie_ai: root.querySelector("#cfg-zombie-ai").value,
      human_ai: root.querySelector("#cfg-human-ai").value,
      healer_ai: root.querySelector("#cfg-healer-ai").value,
      heuristic: heur.value,
      move_time_limit: 0.25,
    };
  }

  function validate() {
    const c = readConfig();
    const err = root.querySelector("#cfg-error");
    let msg = "";
    if (c.n_zombies < 1) msg = "Need at least one zombie.";
    else if (c.n_humans + c.n_healers < 1) msg = "Need at least one human or healer.";
    else if (c.max_rounds < 1) msg = "Rounds must be >= 1.";
    else if (c.heal_cooldown < 1) msg = "Heal cooldown must be >= 1.";
    err.textContent = msg;
    err.classList.toggle("hidden", !msg);
    root.querySelector("#cfg-start").disabled = !!msg;
    return !msg;
  }

  function applyDefaults() {
    mapSel.value = DEFAULTS.map;
    root.querySelector("#cfg-zombies").value = DEFAULTS.n_zombies;
    root.querySelector("#cfg-humans").value = DEFAULTS.n_humans;
    root.querySelector("#cfg-healers").value = DEFAULTS.n_healers;
    root.querySelector("#cfg-rounds").value = DEFAULTS.max_rounds;
    root.querySelector("#cfg-cooldown").value = DEFAULTS.heal_cooldown;
    root.querySelector("#cfg-seed").value = DEFAULTS.seed;
    vision.value = 0; syncVision();
    root.querySelector("#cfg-hidden").checked = false;
    root.querySelector("#cfg-depth").value = DEFAULTS.search_depth;
    root.querySelector("#cfg-zombie-ai").value = DEFAULTS.zombie_ai;
    root.querySelector("#cfg-human-ai").value = DEFAULTS.human_ai;
    root.querySelector("#cfg-healer-ai").value = DEFAULTS.healer_ai;
    heur.value = DEFAULTS.heuristic;
    syncHeuristic();
    validate();
  }

  root.querySelector("#cfg-seed-rand").addEventListener("click", () => {
    root.querySelector("#cfg-seed").value = Math.floor(Math.random() * 1e9);
  });
  root.querySelectorAll("input, select").forEach((el) => el.addEventListener("input", validate));
  root.querySelectorAll("input, select").forEach((el) => el.addEventListener("change", validate));
  root.querySelector("#cfg-reset").addEventListener("click", applyDefaults);

  applyDefaults();

  return {
    root,
    readConfig,
    validate,
    applyDefaults,
    onStart(handler) {
      root.querySelector("#cfg-start").addEventListener("click", () => {
        if (validate()) handler(readConfig());
      });
    },
  };
}

/**
 * Build Compare-tab settings.
 * @param {HTMLElement} root
 * @param {object} helpData
 * @param {{maps:string[], agents:string[]}} options
 */
export function createCompareMenu(root, helpData, options) {
  const agents = (options.agents || AI_OPTIONS).filter((a) => a !== "manual");
  root.innerHTML = `
    <h2>Compare</h2>
    <div class="field" data-key="map"><label>Map <button type="button" class="info">i</button></label>
      <select id="cmp-map"></select></div>
    <div class="field" data-key="compare_role"><label>Vary role <button type="button" class="info">i</button></label>
      <select id="cmp-role"><option value="zombie">Zombies</option><option value="human">Humans</option><option value="healer">Healer</option></select></div>
    <fieldset><legend>AI techniques</legend>
      <div id="cmp-agents" class="check-grid"></div></fieldset>
    <div class="field" data-key="compare_games"><label>Games (10–30) <button type="button" class="info">i</button></label>
      <input id="cmp-games" type="number" min="10" max="30" value="10" /></div>
    <div class="field" data-key="seed"><label>Base seed <button type="button" class="info">i</button></label>
      <input id="cmp-seed" type="number" value="0" /></div>
    <p id="cmp-error" class="form-error hidden"></p>
    <button type="button" id="cmp-run" class="primary">Run</button>
    <div class="progress hidden" id="cmp-progress"><div id="cmp-bar"></div></div>
  `;
  const mapSel = root.querySelector("#cmp-map");
  for (const m of options.maps || []) {
    const o = document.createElement("option");
    o.value = m; o.textContent = m; mapSel.appendChild(o);
  }
  const box = root.querySelector("#cmp-agents");
  for (const a of agents) {
    const id = `cmp-a-${a}`;
    const label = document.createElement("label");
    label.className = "check";
    label.innerHTML = `<input type="checkbox" id="${id}" value="${a}" ${["bfs", "astar", "rulebased"].includes(a) ? "checked" : ""}/> ${a}`;
    box.appendChild(label);
  }
  return {
    read() {
      const names = [...box.querySelectorAll("input:checked")].map((el) => el.value);
      return {
        map: mapSel.value,
        role: root.querySelector("#cmp-role").value,
        agents: names,
        n_games: Number(root.querySelector("#cmp-games").value),
        seed: Number(root.querySelector("#cmp-seed").value),
      };
    },
    validate() {
      const c = this.read();
      const err = root.querySelector("#cmp-error");
      let msg = "";
      if (c.agents.length < 1) msg = "Select at least one AI.";
      else if (c.n_games < 10 || c.n_games > 30) msg = "Games must be 10–30.";
      err.textContent = msg;
      err.classList.toggle("hidden", !msg);
      return !msg;
    },
    onRun(handler) {
      root.querySelector("#cmp-run").addEventListener("click", () => {
        if (this.validate()) handler(this.read());
      });
    },
    setBusy(busy) {
      root.querySelector("#cmp-run").disabled = busy;
      root.querySelector("#cmp-progress").classList.toggle("hidden", !busy);
    },
  };
}
