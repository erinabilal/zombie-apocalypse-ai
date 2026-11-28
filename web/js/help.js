/** Help tab: searchable rich sections from help.json. */

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function settingTip(entry) {
  if (!entry) return "";
  if (typeof entry === "string") return entry;
  return entry.summary || "";
}

/**
 * @param {HTMLElement} root
 * @param {object} helpData
 */
export function renderHelpTab(root, helpData) {
  const sections = helpData.sections || {};
  const agents = helpData.agents || {};
  const settings = helpData.settings || {};
  const controlsTable = helpData.controls_table || [];
  const glossary = helpData.glossary_terms || [];
  const entries = Object.entries(sections);

  root.innerHTML = `
    <div class="help-layout">
      <aside class="help-toc">
        <input id="help-search" type="search" placeholder="Search help…" aria-label="Search help" />
        <nav id="help-nav"></nav>
      </aside>
      <article id="help-content" class="help-content"></article>
    </div>
  `;
  const nav = root.querySelector("#help-nav");
  const content = root.querySelector("#help-content");

  function sectionHaystack(key) {
    const sec = sections[key];
    const parts = [sec.title, sec.body];
    if (sec.steps) parts.push(...sec.steps);
    if (sec.bullets) parts.push(...sec.bullets);
    if (sec.blocks) for (const b of sec.blocks) parts.push(b.heading, b.text);
    if (sec.use_agent_cards) {
      for (const [name, card] of Object.entries(agents)) {
        parts.push(name, typeof card === "string" ? card : `${card.summary} ${card.strong} ${card.weak} ${card.nodes}`);
      }
    }
    if (sec.use_settings_table) {
      for (const [name, s] of Object.entries(settings)) {
        parts.push(name, settingTip(s), s.default, s.range, s.tip);
      }
    }
    if (sec.use_controls_table) {
      for (const row of controlsTable) parts.push(row.control, row.action);
    }
    if (sec.use_glossary) {
      for (const g of glossary) parts.push(g.term, g.def);
    }
    return parts.filter(Boolean).join(" ").toLowerCase();
  }

  function renderAgentCards() {
    return `<div class="agent-cards">${Object.entries(agents).map(([name, card]) => {
      if (typeof card === "string") {
        return `<div class="agent-card"><h4>${escapeHtml(name)}</h4><p>${escapeHtml(card)}</p></div>`;
      }
      return `<div class="agent-card">
        <h4>${escapeHtml(name)}</h4>
        <p>${escapeHtml(card.summary || "")}</p>
        <p><strong>Strong:</strong> ${escapeHtml(card.strong || "")}</p>
        <p><strong>Weak:</strong> ${escapeHtml(card.weak || "")}</p>
        <p><strong>Nodes expanded:</strong> ${escapeHtml(card.nodes || "")}</p>
      </div>`;
    }).join("")}</div>`;
  }

  function renderSettingsTable() {
    const rows = Object.entries(settings).map(([key, s]) => {
      const summary = typeof s === "string" ? s : (s.summary || "");
      const def = typeof s === "object" ? (s.default || "—") : "—";
      const range = typeof s === "object" ? (s.range || "—") : "—";
      const tip = typeof s === "object" ? (s.tip || "") : "";
      return `<tr>
        <td><code>${escapeHtml(key)}</code></td>
        <td>${escapeHtml(summary)}</td>
        <td>${escapeHtml(def)}</td>
        <td>${escapeHtml(range)}</td>
        <td>${escapeHtml(tip)}</td>
      </tr>`;
    }).join("");
    return `<div class="table-wrap"><table class="help-table">
      <thead><tr><th>Setting</th><th>What it does</th><th>Default</th><th>Range</th><th>Example tip</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
  }

  function renderControlsTable() {
    const rows = controlsTable.map((r) =>
      `<tr><td>${escapeHtml(r.control)}</td><td>${escapeHtml(r.action)}</td></tr>`).join("");
    return `<div class="table-wrap"><table class="help-table">
      <thead><tr><th>Control / key</th><th>Action</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
  }

  function renderGlossary() {
    const rows = glossary.map((g) =>
      `<tr><td><strong>${escapeHtml(g.term)}</strong></td><td>${escapeHtml(g.def)}</td></tr>`).join("");
    return `<div class="table-wrap"><table class="help-table">
      <thead><tr><th>Term</th><th>Meaning</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
  }

  function show(key) {
    const sec = sections[key];
    if (!sec) return;
    let html = `<h2>${escapeHtml(sec.title)}</h2><p>${escapeHtml(sec.body || "")}</p>`;
    if (sec.steps?.length) {
      html += `<ol class="help-steps">${sec.steps.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ol>`;
    }
    if (sec.blocks?.length) {
      html += sec.blocks.map((b) =>
        `<section class="help-block"><h3>${escapeHtml(b.heading)}</h3><p>${escapeHtml(b.text)}</p></section>`).join("");
    }
    if (sec.bullets?.length) {
      html += `<ul class="help-bullets">${sec.bullets.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>`;
    }
    if (sec.use_settings_table) html += renderSettingsTable();
    if (sec.use_controls_table) html += renderControlsTable();
    if (sec.use_agent_cards) html += renderAgentCards();
    if (sec.use_glossary) html += renderGlossary();
    content.innerHTML = html;
    nav.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.dataset.key === key));
  }

  for (const [key, sec] of entries) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.key = key;
    btn.textContent = sec.title;
    btn.addEventListener("click", () => show(key));
    nav.appendChild(btn);
  }

  root.querySelector("#help-search").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    nav.querySelectorAll("button").forEach((btn) => {
      const hay = sectionHaystack(btn.dataset.key);
      btn.classList.toggle("hidden", Boolean(q) && !hay.includes(q));
    });
  });

  if (entries.length) show(entries[0][0]);
}

/** Tip text for info icons (supports string or {summary}). */
export function tipForSetting(helpData, key) {
  return settingTip(helpData?.settings?.[key]);
}

/**
 * Render Rules tab with illustrated diagrams.
 * @param {HTMLElement} root
 */
export function renderRulesTab(root) {
  root.innerHTML = `
    <h2>Game rules</h2>
    <p class="rules-lead">A turn-based maze. <strong>Zombies</strong> (green, Z) try to infect every human-team agent before time runs out.
    <strong>Humans</strong> (blue, H) try to survive. The <strong>healer</strong> (white with red cross, +) can cure an adjacent zombie back into a human when cooldown is ready. Healers count as humans for winning.</p>

    <div class="rules-grid">
      <figure class="rules-card">
        <svg viewBox="0 0 240 150" width="100%" aria-label="Infection diagram">
          <defs>
            <marker id="arrowInf" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#e8edf7"/>
            </marker>
          </defs>
          <rect width="240" height="150" rx="8" fill="#121826"/>
          <rect x="20" y="30" width="40" height="40" fill="#d9e0ea" stroke="#2b3347"/>
          <rect x="60" y="30" width="40" height="40" fill="#d9e0ea" stroke="#2b3347"/>
          <rect x="100" y="30" width="40" height="40" fill="#d9e0ea" stroke="#2b3347"/>
          <circle cx="40" cy="50" r="14" fill="#3ecf8e"/><text x="40" y="54" text-anchor="middle" fill="#062416" font-size="11" font-weight="700">Z0</text>
          <circle cx="120" cy="50" r="14" fill="#4d8dff"/><text x="120" y="54" text-anchor="middle" fill="#fff" font-size="11" font-weight="700">H1</text>
          <path d="M56 50 H100" stroke="#e8edf7" stroke-width="2" marker-end="url(#arrowInf)"/>
          <text x="120" y="100" text-anchor="middle" fill="#9aa6bf" font-size="12">Orthogonally adjacent</text>
          <text x="120" y="118" text-anchor="middle" fill="#9aa6bf" font-size="12">→ infect after every action</text>
          <text x="120" y="138" text-anchor="middle" fill="#7a869e" font-size="11">Chain infection possible in one action</text>
        </svg>
        <figcaption><strong>Infection.</strong> Checked after every individual action. One move can infect several humans. An infected healer becomes a zombie.</figcaption>
      </figure>

      <figure class="rules-card">
        <svg viewBox="0 0 240 150" width="100%" aria-label="Healing diagram">
          <rect width="240" height="150" rx="8" fill="#121826"/>
          <circle cx="70" cy="55" r="16" fill="#f4f4f4" stroke="#b00020" stroke-width="3"/>
          <text x="70" y="60" text-anchor="middle" fill="#b00020" font-size="16" font-weight="700">+</text>
          <circle cx="140" cy="55" r="16" fill="#3ecf8e"/><text x="140" y="59" text-anchor="middle" fill="#062416" font-size="11" font-weight="700">Z</text>
          <text x="105" y="30" text-anchor="middle" fill="#e8edf7" font-size="12">cooldown = 0</text>
          <path d="M90 55 H120" stroke="#e8edf7" stroke-width="2" marker-end="url(#arrowInf)"/>
          <rect x="50" y="88" width="140" height="14" rx="3" fill="#333"/>
          <rect x="50" y="88" width="140" height="14" rx="3" fill="#3ecf8e"/>
          <text x="120" y="122" text-anchor="middle" fill="#9aa6bf" font-size="12">Heal: face zombie, do not move</text>
          <text x="120" y="140" text-anchor="middle" fill="#7a869e" font-size="11">STAY never heals · next heal at T+cooldown</text>
        </svg>
        <figcaption><strong>Healing.</strong> Only the healer. Direction into an adjacent zombie while ready. Cooldown ticks at the start of the healer’s own turns.</figcaption>
      </figure>

      <figure class="rules-card">
        <svg viewBox="0 0 240 150" width="100%" aria-label="Turn order diagram">
          <rect width="240" height="150" rx="8" fill="#121826"/>
          <text x="120" y="28" text-anchor="middle" fill="#e8edf7" font-size="13" font-weight="600">One round</text>
          <rect x="20" y="44" width="50" height="36" rx="6" fill="#3ecf8e33" stroke="#3ecf8e"/>
          <text x="45" y="66" text-anchor="middle" fill="#e8edf7" font-size="11">id 0</text>
          <rect x="85" y="44" width="50" height="36" rx="6" fill="#4d8dff33" stroke="#4d8dff"/>
          <text x="110" y="66" text-anchor="middle" fill="#e8edf7" font-size="11">id 1</text>
          <rect x="150" y="44" width="50" height="36" rx="6" fill="#f4f4f433" stroke="#f4f4f4"/>
          <text x="175" y="66" text-anchor="middle" fill="#e8edf7" font-size="11">id 2…</text>
          <path d="M70 62 H85" stroke="#9aa6bf" stroke-width="2"/>
          <path d="M135 62 H150" stroke="#9aa6bf" stroke-width="2"/>
          <text x="120" y="110" text-anchor="middle" fill="#9aa6bf" font-size="12">Ascending id order</text>
          <text x="120" y="130" text-anchor="middle" fill="#7a869e" font-size="11">Infected/healed agents skip rest of round</text>
        </svg>
        <figcaption><strong>Turns.</strong> Every agent acts once per round in ascending id order unless skipped after infection or healing.</figcaption>
      </figure>
    </div>

    <div class="rules-wins panel-inset">
      <h3>Win conditions (checked after every action and at round end)</h3>
      <ol>
        <li><strong>all_infected</strong> — no human-team agents left → zombies win.</li>
        <li><strong>no_zombies</strong> — no zombies left → humans win.</li>
        <li><strong>time_limit</strong> — after the final round: zombies win only if zombies &gt; humans; a tie is a human win.</li>
      </ol>
      <p>Illegal moves into walls, out of bounds, or occupied cells become STAY and count as illegal actions. No two agents share a cell. Movement is orthogonal only; terrain cost affects planning, not speed.</p>
    </div>
  `;
}
