const api = {
  summary: "/api/summary",
  tools: "/api/tools",
  recs: "/api/recommendations",
  copilot: "/api/recommendations" // placeholder (no real LLM here)
};

document.addEventListener("DOMContentLoaded", async () => {
  await loadSummary();
  await loadFilters();
  await loadTools();
  await loadRecs();
  setupHandlers();
});

async function loadSummary() {
  const r = await fetch(api.summary);
  const j = await r.json();
  const s = j.stats;
  const whitespace = j.whitespace;
  const el = document.getElementById("summary-stats");
  el.innerHTML = `
    <div><strong>Total tools:</strong> ${s.total}</div>
    <div><strong>Open-source tools:</strong> ${s.open_source_pct ?? "N/A"}%</div>
    <div><strong>APIs available:</strong> ${s.apis_pct ?? "N/A"}%</div>
    <div><strong>Latest release year:</strong> ${s.latest_year ?? "N/A"}</div>
    <div class="mt-2"><strong>Major gap:</strong> ${whitespace.major_gap_recommendation}</div>
  `;

  // chart categories
  const ctx = document.getElementById("catChart").getContext("2d");
  const cats = j.stats.by_category || {};
  const labels = Object.keys(cats);
  const data = Object.values(cats);
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'tools by category', data, backgroundColor: '#0d6efd' }]
    },
    options: { responsive:true, maintainAspectRatio:false, scales:{y:{beginAtZero:true}}}
  });
}

async function loadFilters() {
  const r = await fetch(api.tools);
  const j = await r.json();
  const rows = j.rows;
  // extract unique categories & modalities
  const cats = new Set();
  const mods = new Set();
  rows.forEach(row => {
    if (row.category_canonical) cats.add(row.category_canonical);
    if (row.modality_canonical) mods.add(row.modality_canonical);
  });
  const selCat = document.getElementById("filter-category");
  Array.from(cats).sort().forEach(c => {
    const o = document.createElement("option"); o.value = c; o.textContent = c; selCat.appendChild(o);
  });
  const selMod = document.getElementById("filter-modality");
  Array.from(mods).sort().forEach(m => {
    const o = document.createElement("option"); o.value = m; o.textContent = m; selMod.appendChild(o);
  });
}

async function loadTools() {
  const selCat = document.getElementById("filter-category").value;
  const selMod = document.getElementById("filter-modality").value;
  const selOpen = document.getElementById("filter-open").value;
  const params = new URLSearchParams();
  if (selCat) params.set("category", selCat);
  if (selMod) params.set("modality", selMod);
  if (selOpen) params.set("open", selOpen);
  const url = "/api/tools?" + params.toString();
  const r = await fetch(url);
  const j = await r.json();
  const body = document.getElementById("tools-body");
  body.innerHTML = "";
  j.rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.tool_name ?? ""}</td>
      <td>${row.company ?? ""}</td>
      <td>${row.category_canonical ?? ""}</td>
      <td>${row.modality_canonical ?? ""}</td>
      <td>${row.open_source == 1 ? "Yes" : "No"}</td>
      <td>${row.api_available == 1 ? "Yes" : "No"}</td>
      <td>${row.release_year ?? ""}</td>
    `;
    body.appendChild(tr);
  });
}

async function loadRecs() {
  const r = await fetch(api.recs);
  const j = await r.json();
  const recs = j.recommendations || [];
  const el = document.getElementById("recommender");
  el.innerHTML = "";
  recs.forEach(r => {
    const div = document.createElement("div");
    div.className = "mb-2";
    div.innerHTML = `<strong>${r.phase}</strong><ul>${r.features.map(f => `<li>${f}</li>`).join("")}</ul>`;
    el.appendChild(div);
  });
}

function setupHandlers() {
  document.getElementById("btn-refresh").addEventListener("click", async () => {
    await loadTools();
  });
  document.getElementById("btn-reset").addEventListener("click", async () => {
    document.getElementById("filter-category").value = "";
    document.getElementById("filter-modality").value = "";
    document.getElementById("filter-open").value = "";
    await loadTools();
  });
  document.getElementById("open-copilot").addEventListener("click", () => {
    const modal = new bootstrap.Modal(document.getElementById('copilotModal'));
    modal.show();
  });

  document.getElementById("copilot-send").addEventListener("click", async () => {
    const prompt = document.getElementById("copilot-prompt").value.trim();
    if (!prompt) return;
    document.getElementById("copilot-response").textContent = "Thinking (prototype)...";
    // quick local "copilot" mimic: return extracted recommendations or a canned explanation
    const local = cannedCopilot(prompt);
    document.getElementById("copilot-response").textContent = local;
  });

  document.getElementById("modal-send").addEventListener("click", async () => {
    const prompt = document.getElementById("modal-prompt").value.trim();
    if (!prompt) return;
    // this prototype does not call an LLM; it uses canned heuristics
    const resp = cannedCopilot(prompt);
    document.getElementById("modal-response").innerHTML = `<pre class="small bg-light p-2">${resp}</pre>`;
  });
}

function cannedCopilot(prompt) {
  const p = prompt.toLowerCase();
  if (p.includes("impermanent") || p.includes("il") || p.includes("impermanent loss")) {
    return "Impermanent Loss (IL) arises when two assets in a CPMM diverge in price. Deterministic calc: IL = 1 - (2 * sqrt(R) / (1+R)) where R = price_ratio. In Velar, use the Velar Math Engine to compute exact LP share changes given pool reserves.";
  }
  if (p.includes("staking") || p.includes("ido")) {
    return "Staking guidance: staking $VELAR grants IDO tickets and fee share. For a projection, provide your stake amount and the tool will compute expected ticket chances and APY estimates based on current pool yields.";
  }
  if (p.includes("what to build") || p.includes("recommend")) {
    return "Recommended: Build Velar Copilot (swap & LP explainers), Perps Risk Engine, AI Market-Maker assistant, Governance Copilot. Prioritize deterministic math + on-chain indexer.";
  }
  return "Prototype Copilot: This environment is a non-LLM prototype. For live natural language answers, integrate a fine-tuned LLM with a deterministic math engine and on-chain RAG.";
}
