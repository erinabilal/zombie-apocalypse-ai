/** Canvas renderer with optional vision dimming and belief heat map. */

const ROLE_STYLE = {
  zombie: { fill: "#3ecf8e", letter: "Z" },
  human: { fill: "#4d8dff", letter: "H" },
  healer: { fill: "#f4f4f4", letter: "+", text: "#b00020" },
};

/**
 * @param {HTMLCanvasElement} canvas
 * @param {object} mapInfo
 * @param {object} state
 * @param {object} [opts]
 */
export function drawBoard(canvas, mapInfo, state, opts = {}) {
  if (!canvas || !mapInfo || !state) return;
  const {
    selectedId = null,
    visibleCells = null,
    beliefCells = null,
    anim = null,
  } = opts;

  const ctx = canvas.getContext("2d");
  const cols = mapInfo.width;
  const rows = mapInfo.height;
  const parent = canvas.parentElement;
  const maxW = parent ? parent.clientWidth - 16 : 640;
  const maxH = Math.min(560, window.innerHeight * 0.55);
  const cell = Math.max(10, Math.floor(Math.min(maxW / cols, maxH / rows)));
  const width = cell * cols;
  const height = cell * rows;
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  ctx.clearRect(0, 0, width, height);

  const visibleSet = visibleCells
    ? new Set(visibleCells.map(([x, y]) => `${x},${y}`))
    : null;
  const beliefMap = new Map();
  if (beliefCells) {
    for (const [x, y, p] of beliefCells) beliefMap.set(`${x},${y}`, p);
  }

  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const tile = mapInfo.cells[y][x];
      const key = `${x},${y}`;
      if (tile.wall) {
        ctx.fillStyle = "#2a2f3a";
        ctx.fillRect(x * cell, y * cell, cell, cell);
      } else {
        const shade = Math.min(0.45, (tile.cost - 1) * 0.12);
        ctx.fillStyle = `rgb(${217 - shade * 80}, ${224 - shade * 60}, ${234 - shade * 40})`;
        ctx.fillRect(x * cell, y * cell, cell, cell);
        if (tile.cost > 1) {
          ctx.fillStyle = "rgba(20,30,40,0.35)";
          ctx.font = `${Math.max(8, cell * 0.32)}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(String(tile.cost), x * cell + cell / 2, y * cell + cell / 2);
        }
        if (beliefMap.has(key)) {
          const p = beliefMap.get(key);
          ctx.fillStyle = `rgba(220, 40, 40, ${Math.min(0.55, p * 0.8)})`;
          ctx.fillRect(x * cell, y * cell, cell, cell);
        }
        if (visibleSet && !visibleSet.has(key)) {
          ctx.fillStyle = "rgba(8,10,16,0.55)";
          ctx.fillRect(x * cell, y * cell, cell, cell);
        }
      }
    }
  }

  for (const agent of state.agents || []) {
    const style = ROLE_STYLE[agent.role] || ROLE_STYLE.human;
    const cx = agent.x * cell + cell / 2;
    const cy = agent.y * cell + cell / 2;
    const r = cell * 0.36;
    let fill = style.fill;
    if (anim && anim.id === agent.id) {
      fill = anim.kind === "infect" ? "#3ecf8e" : "#4d8dff";
    }
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    if (selectedId === agent.id) {
      ctx.lineWidth = 3;
      ctx.strokeStyle = "#ffd27a";
    } else {
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#0b1020";
    }
    ctx.stroke();
    ctx.fillStyle = style.text || "#0b1020";
    ctx.font = `bold ${Math.max(10, cell * 0.3)}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(`${style.letter}${agent.id}`, cx, cy);

    if (agent.role === "healer") {
      const barW = cell * 0.7;
      const barH = Math.max(3, cell * 0.08);
      const bx = cx - barW / 2;
      const by = cy + r + 2;
      ctx.fillStyle = "#333";
      ctx.fillRect(bx, by, barW, barH);
      if (agent.cooldown > 0) {
        ctx.fillStyle = "#e35d6a";
        ctx.fillRect(bx, by, barW * Math.min(1, agent.cooldown / 5), barH);
      } else {
        ctx.fillStyle = "#3ecf8e";
        ctx.fillRect(bx, by, barW, barH);
      }
    }
  }
}

/**
 * Hit-test agent under canvas click.
 * @param {MouseEvent} event
 * @param {HTMLCanvasElement} canvas
 * @param {object} mapInfo
 * @param {object} state
 */
export function agentAtEvent(event, canvas, mapInfo, state) {
  if (!mapInfo || !state) return null;
  const rect = canvas.getBoundingClientRect();
  const cell = canvas.width / mapInfo.width;
  const x = Math.floor(((event.clientX - rect.left) / rect.width) * mapInfo.width);
  const y = Math.floor(((event.clientY - rect.top) / rect.height) * mapInfo.height);
  return state.agents.find((a) => a.x === x && a.y === y) || null;
}
