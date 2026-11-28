/** Chart.js helpers for Compare and Results tabs. Chart.js loaded from CDN on window. */

/**
 * @param {HTMLCanvasElement} canvas
 * @param {Array<{agent:string, win_rate:number, avg_rounds:number, avg_nodes_expanded:number, avg_time_per_move:number}>} rows
 * @param {string} metric
 * @param {string} title
 */
export function renderBarChart(canvas, rows, metric, title) {
  if (!window.Chart) {
    console.warn("Chart.js not loaded");
    return null;
  }
  const existing = canvas._chart;
  if (existing) existing.destroy();
  const chart = new window.Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: rows.map((r) => r.agent),
      datasets: [{
        label: title,
        data: rows.map((r) => r[metric]),
        backgroundColor: "#3ecf8e99",
        borderColor: "#3ecf8e",
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        title: { display: true, text: title, color: "#e8edf7" },
      },
      scales: {
        x: { ticks: { color: "#9aa6bf" }, grid: { color: "#2b3347" } },
        y: {
          ticks: { color: "#9aa6bf" },
          grid: { color: "#2b3347" },
        },
      },
    },
  });
  canvas._chart = chart;
  return chart;
}

/**
 * Fill a results HTML table.
 * @param {HTMLElement} table
 * @param {Array<object>} rows
 */
export function fillResultsTable(table, rows) {
  const headers = ["agent", "win_rate", "avg_rounds", "avg_nodes_expanded", "avg_time_per_move"];
  table.innerHTML = `<thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>`;
  const body = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = headers.map((h) => {
      let v = row[h];
      if (typeof v === "number") v = h === "win_rate" ? v.toFixed(3) : v.toFixed(3);
      return `<td>${v}</td>`;
    }).join("");
    body.appendChild(tr);
  }
  table.appendChild(body);
}
