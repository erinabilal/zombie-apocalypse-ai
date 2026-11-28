/** Playback control bar and keyboard manual input. */

/**
 * @param {HTMLElement} root
 * @param {object} handlers
 */
export function createControls(root, handlers) {
  root.innerHTML = `
    <div class="control-bar">
      <button type="button" id="ctl-start" class="primary">Start / Restart</button>
      <button type="button" id="ctl-play" disabled>Play</button>
      <button type="button" id="ctl-step" disabled>Step</button>
      <button type="button" id="ctl-round" disabled>Step Round</button>
      <label class="inline" data-key="speed">Speed
        <input id="ctl-speed" type="range" min="1" max="20" value="5" />
        <span id="ctl-speed-val">5/s</span>
        <button type="button" class="info">i</button>
      </label>
      <label class="inline check" data-key="vision_overlay">
        <input id="ctl-vision" type="checkbox" /> Vision overlay
        <button type="button" class="info">i</button>
      </label>
      <label class="inline check" data-key="belief_overlay">
        <input id="ctl-belief" type="checkbox" /> Belief heat map
        <button type="button" class="info">i</button>
      </label>
      <button type="button" id="ctl-replay" class="secondary" disabled>Download replay</button>
    </div>
    <p id="ctl-toast" class="toast hidden" role="status"></p>
  `;

  const playBtn = root.querySelector("#ctl-play");
  const speed = root.querySelector("#ctl-speed");
  const speedVal = root.querySelector("#ctl-speed-val");
  speed.addEventListener("input", () => {
    speedVal.textContent = `${speed.value}/s`;
    handlers.onSpeed?.(Number(speed.value));
  });
  root.querySelector("#ctl-start").addEventListener("click", () => handlers.onStart?.());
  playBtn.addEventListener("click", () => handlers.onPlayToggle?.());
  root.querySelector("#ctl-step").addEventListener("click", () => handlers.onStep?.());
  root.querySelector("#ctl-round").addEventListener("click", () => handlers.onRound?.());
  root.querySelector("#ctl-vision").addEventListener("change", (e) => handlers.onVision?.(e.target.checked));
  root.querySelector("#ctl-belief").addEventListener("change", (e) => handlers.onBelief?.(e.target.checked));
  root.querySelector("#ctl-replay").addEventListener("click", () => handlers.onReplay?.());

  let toastTimer = null;
  return {
    setPlaying(playing) {
      playBtn.textContent = playing ? "Pause" : "Play";
    },
    setEnabled(enabled) {
      for (const id of ["#ctl-play", "#ctl-step", "#ctl-round", "#ctl-replay"]) {
        root.querySelector(id).disabled = !enabled;
      }
    },
    getSpeed() {
      return Number(speed.value);
    },
    toast(msg) {
      const el = root.querySelector("#ctl-toast");
      el.textContent = msg;
      el.classList.remove("hidden");
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => el.classList.add("hidden"), 1200);
    },
    bindInfo(helpSettings) {
      root.querySelectorAll("[data-key]").forEach((wrap) => {
        const btn = wrap.querySelector(".info");
        if (!btn) return;
        const entry = helpSettings[wrap.dataset.key];
        btn.title = typeof entry === "string" ? entry : (entry?.summary || "");
      });
    },
  };
}

const KEY_ACTIONS = {
  ArrowUp: "UP", w: "UP", W: "UP",
  ArrowDown: "DOWN", s: "STAY", S: "STAY", " ": "STAY",
  ArrowLeft: "LEFT", a: "LEFT", A: "LEFT",
  ArrowRight: "RIGHT", d: "RIGHT", D: "RIGHT",
};

/**
 * Attach keyboard listener for manual play. Returns a dispose function.
 * @param {(action:string)=>void} onAction
 * @param {()=>boolean} isManualTurn
 */
export function bindManualKeys(onAction, isManualTurn) {
  const handler = (e) => {
    if (!isManualTurn()) return;
    // Allow S for stay; W/A/D for move. Space stay.
    let action = KEY_ACTIONS[e.key];
    if (e.key === "s" || e.key === "S") {
      // Prefer STAY; shift+S still stay. (WASD: S is stay per brief)
      action = "STAY";
    }
    if (!action) return;
    e.preventDefault();
    onAction(action);
  };
  window.addEventListener("keydown", handler);
  return () => window.removeEventListener("keydown", handler);
}
