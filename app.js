async function loadJSON(p) { const r = await fetch(p); if (!r.ok) throw new Error(p); return r.json(); }

const METRIC_COLS = [
  ["artificialanalysis", "intelligence_index", "AA Intel"],
  ["artificialanalysis", "coding_index", "AA Coding"],
  ["livebench", "average", "LiveBench"],
  ["aider", "pass_rate", "Aider %"],
  ["llmstats", "rating", "llm-stats"],
  ["openrouter", "tokens_total", "OR usage"],
  ["artificialanalysis", "price_blended_per_1m", "$/1M blend"],
];

function fmt(v) {
  if (v == null) return "–";
  if (v >= 1e9) return (v / 1e9).toFixed(1) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(1) + "M";
  return typeof v === "number" ? +v.toFixed(2) : v;
}

function renderChanges(changes, models) {
  const ul = document.getElementById("changes-list");
  if (!changes.length) { ul.innerHTML = "<li>No changes since last build.</li>"; return; }
  for (const e of changes) {
    const li = document.createElement("li");
    const name = models[e.model]?.name ?? e.model;
    if (e.type === "new_model") li.textContent = `🆕 ${name} appeared`;
    else if (e.type === "rank_change")
      li.textContent = `${e.to < e.from ? "📈" : "📉"} ${name}: #${e.from} → #${e.to} on ${e.source}`;
    else if (e.type === "source_stale") li.textContent = `⚠️ ${e.source} fetch failing (stale data shown)`;
    ul.appendChild(li);
  }
}

function renderTable(latest) {
  const t = document.getElementById("model-table");
  const head = "<tr><th data-k='name'>Model</th><th>Vendor</th>" +
    METRIC_COLS.map((c, i) => `<th data-i="${i}">${c[2]}</th>`).join("") + "</tr>";
  const rows = Object.entries(latest.models)
    .filter(([, m]) => Object.keys(m.scores).length)
    .map(([id, m]) => ({ id, name: m.name, vendor: m.vendor,
      vals: METRIC_COLS.map(([s, k]) => m.scores[s]?.[k] ?? null) }));
  let sortI = 0, desc = true;
  function draw() {
    rows.sort((a, b) => ((b.vals[sortI] ?? -Infinity) - (a.vals[sortI] ?? -Infinity)) * (desc ? 1 : -1));
    t.innerHTML = head + rows.map(r =>
      `<tr><td>${r.name}</td><td>${r.vendor}</td>` +
      r.vals.map(v => `<td>${fmt(v)}</td>`).join("") + "</tr>").join("");
    t.querySelectorAll("th[data-i]").forEach(th =>
      th.onclick = () => { const i = +th.dataset.i; desc = i === sortI ? !desc : true; sortI = i; draw(); });
  }
  draw();
}

function renderSources(sourcesDoc, latest) {
  const box = document.getElementById("source-cards");
  const byTier = {};
  for (const s of sourcesDoc.sources) (byTier[s.tier] ??= []).push(s);
  for (const tier of Object.keys(byTier).sort()) {
    const h = document.createElement("h3");
    h.textContent = `Tier ${tier} — ${byTier[tier][0].tier_name}`;
    box.appendChild(h);
    const grid = document.createElement("div"); grid.className = "grid";
    for (const s of byTier[tier]) {
      const card = document.createElement("div"); card.className = "card";
      const status = latest.sources[s.id];
      let top = "";
      if (s.fetched && status) {
        const stale = status.ok ? "" : ` <span class="stale">stale since ${status.stale_since ?? "?"}</span>`;
        const top5 = (latest.ranks[s.id] || []).slice(0, 5)
          .map((mid, i) => `<li>${i + 1}. ${latest.models[mid]?.name ?? mid}</li>`).join("");
        top = `<ol class="top5">${top5}</ol><small>updated ${status.fetched_at ?? "?"}${stale}</small>`;
      }
      card.innerHTML = `<a href="${s.url}"><strong>${s.name}</strong></a>
        <p>${s.note ?? ""}</p>${top}`;
      grid.appendChild(card);
    }
    box.appendChild(grid);
  }
}

function renderCharts(latest, trends) {
  const pts = Object.entries(latest.models).map(([id, m]) => {
    const aa = m.scores.artificialanalysis;
    return aa?.intelligence_index != null && aa?.price_blended_per_1m != null
      ? { x: aa.price_blended_per_1m, y: aa.intelligence_index, label: m.name } : null;
  }).filter(Boolean);
  new Chart(document.getElementById("scatter"), {
    type: "scatter",
    data: { datasets: [{ label: "Intelligence vs $/1M (blended)", data: pts }] },
    options: { plugins: { tooltip: { callbacks: {
        label: c => `${c.raw.label}: ${c.raw.y} @ $${c.raw.x}/1M` } } },
      scales: { x: { title: { display: true, text: "$ per 1M tokens (blended)" }, type: "logarithmic" },
                y: { title: { display: true, text: "AA Intelligence Index" } } } },
  });
  const sp = document.getElementById("sparklines");
  for (const [mid, srcs] of Object.entries(trends)) {
    const series = srcs.artificialanalysis?.intelligence_index;
    if (!series || series.length < 2) continue;
    const wrap = document.createElement("div"); wrap.className = "spark";
    wrap.innerHTML = `<span>${latest.models[mid]?.name ?? mid}</span><canvas height="40"></canvas>`;
    sp.appendChild(wrap);
    new Chart(wrap.querySelector("canvas"), {
      type: "line",
      data: { labels: series.map(p => p[0]),
              datasets: [{ data: series.map(p => p[1]), pointRadius: 0, borderWidth: 1.5 }] },
      options: { plugins: { legend: { display: false } },
                 scales: { x: { display: false }, y: { display: false } } },
    });
  }
}

(async () => {
  const [latest, trends, sourcesDoc] = await Promise.all([
    loadJSON("data/latest.json"), loadJSON("data/trends.json"), loadJSON("data/sources.json")]);
  document.getElementById("generated-at").textContent = `Data as of ${latest.generated_at}`;
  renderChanges(latest.changes ?? [], latest.models);
  renderTable(latest);
  renderSources(sourcesDoc, latest);
  renderCharts(latest, trends);
})().catch(e => { document.body.insertAdjacentHTML("afterbegin",
  `<p class="error">Failed to load data: ${e.message}</p>`); });
