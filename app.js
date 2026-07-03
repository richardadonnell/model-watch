async function loadJSON(p) { const r = await fetch(p); if (!r.ok) throw new Error(p); return r.json(); }

const METRIC_COLS = [
  ["artificialanalysis", "intelligence_index", "AA Intel"],
  ["artificialanalysis", "coding_index", "AA Coding"],
  ["livebench", "average", "LiveBench"],
  ["aider", "pass_rate", "Aider %"],
  ["openrouter", "tokens_total", "OR usage"],
  ["artificialanalysis", "price_blended_per_1m", "$/1M blend"],
];

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

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
    else if (e.type === "price_change")
      li.textContent = `💰 ${name}: $${(+e.from).toFixed(2)} → $${(+e.to).toFixed(2)} /1M out`;
    ul.appendChild(li);
  }
}

function renderTable(latest) {
  const t = document.getElementById("model-table");
  const rows = Object.entries(latest.models)
    .filter(([, m]) => Object.keys(m.scores).length)
    .map(([id, m]) => ({ id, name: m.name, vendor: m.vendor,
      vals: METRIC_COLS.map(([s, k]) => m.scores[s]?.[k] ?? null) }));
  let sortI = 0, desc = true;
  function draw() {
    const arrow = i => i === sortI ? (desc ? " ▼" : " ▲") : "";
    const head = "<tr><th data-k='name'>Model</th><th>Vendor</th>" +
      METRIC_COLS.map((c, i) => {
        const active = i === sortI;
        const sort = active ? ` aria-sort="${desc ? "descending" : "ascending"}"` : "";
        return `<th data-i="${i}" tabindex="0" scope="col"${active ? ' class="sorted"' : ""}${sort}>${esc(c[2])}${arrow(i)}</th>`;
      }).join("") + "</tr>";
    rows.sort((a, b) => ((b.vals[sortI] ?? -Infinity) - (a.vals[sortI] ?? -Infinity)) * (desc ? 1 : -1));
    const body = rows.map(r =>
      `<tr><td>${esc(r.name)}</td><td>${esc(r.vendor)}</td>` +
      r.vals.map((v, i) => {
        const cls = i === sortI ? ' class="col-active"' : "";
        return `<td${cls}>${v == null ? '<span class="nil">–</span>' : esc(fmt(v))}</td>`;
      }).join("") + "</tr>").join("");
    t.innerHTML = `<thead>${head}</thead><tbody>${body}</tbody>`;
    t.querySelectorAll("th[data-i]").forEach(th => {
      const act = () => {
        const i = +th.dataset.i;
        desc = i === sortI ? !desc : true; sortI = i;
        draw();
        t.querySelector("th.sorted")?.focus();
      };
      th.onclick = act;
      th.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); act(); } };
    });
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
        if (!status.ok && !status.fetched_at) {
          // Never fetched successfully — no data to be "stale", just absent.
          top = `<small class="asof">no data yet</small>`;
        } else {
          const stale = status.ok ? "" : ` <span class="stale">stale since ${esc(status.stale_since ?? "?")}</span>`;
          const top5 = (latest.ranks[s.id] || []).slice(0, 5)
            .map((mid, i) => `<li>${i + 1}. ${esc(latest.models[mid]?.name ?? mid)}</li>`).join("");
          // Some sources serve older data than the fetch time — surface the
          // source's own data date when it differs from the fetch day.
          const fetchDay = (status.fetched_at ?? "").slice(0, 10);
          const dataAsOf = status.data_date && status.data_date !== fetchDay
            ? ` <span class="asof">data as of ${esc(status.data_date)}</span>` : "";
          top = `<ol class="top5">${top5}</ol><small>updated ${esc(status.fetched_at ?? "?")}${dataAsOf}${stale}</small>`;
        }
      }
      card.innerHTML = `<a href="${esc(s.url)}"><strong>${esc(s.name)}</strong></a>
        <p>${esc(s.note ?? "")}</p>${top}`;
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
  const scatterEl = document.getElementById("scatter");
  if (!pts.length) {
    scatterEl.replaceWith(Object.assign(document.createElement("p"),
      { className: "asof", textContent: "Intelligence-vs-price chart needs Artificial Analysis data (add an API key)." }));
    return;
  }
  // Instrument palette for canvas (Chart.js color engine can't parse oklch()).
  const C = {
    plot: "#b39a72", ink: "#b6a893", mute: "#8a8171", grid: "#38342c",
    accent: "#e3aa5c", surface: "#2e2a24", line: "#4a453b", fg: "#eceae4",
  };
  const SANS = '"Saira Semi Condensed", system-ui, sans-serif';
  const MONO = '"Geist Mono", ui-monospace, monospace';
  Chart.defaults.font.family = SANS;
  Chart.defaults.color = C.mute;

  // Direct-label only the two standouts: top intelligence, best value (intel/$).
  const topIntel = [...pts].sort((a, b) => b.y - a.y)[0];
  const bestValue = [...pts].sort((a, b) => b.y / b.x - a.y / a.x)[0];
  const labelled = new Set([topIntel, bestValue]);
  const callouts = {
    id: "callouts",
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      ctx.save();
      ctx.font = "600 11px " + SANS;
      ctx.fillStyle = C.accent;
      ctx.textAlign = "left";
      chart.getDatasetMeta(0).data.forEach((pt, i) => {
        if (labelled.has(pts[i])) ctx.fillText(pts[i].label, pt.x + 8, pt.y + 4);
      });
      ctx.restore();
    },
  };

  const axis = (text) => ({
    title: { display: true, text, color: C.mute, font: { family: SANS, size: 12 } },
    grid: { color: C.grid, drawTicks: false },
    border: { color: C.line },
    ticks: { color: C.mute, font: { family: MONO, size: 10 } },
  });
  new Chart(scatterEl, {
    type: "scatter",
    data: { datasets: [{
      data: pts, pointBackgroundColor: C.plot, pointBorderColor: "transparent",
      pointRadius: 4, pointHoverRadius: 7, pointHoverBackgroundColor: C.accent,
    }] },
    options: {
      layout: { padding: { right: 76, top: 8 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: C.surface, titleColor: C.fg, bodyColor: C.ink,
          borderColor: C.line, borderWidth: 1, padding: 8, displayColors: false,
          titleFont: { family: SANS, weight: "600" }, bodyFont: { family: MONO },
          callbacks: {
            title: (c) => c[0].raw.label,
            label: (c) => `intel ${c.raw.y}  ·  $${c.raw.x}/1M`,
          },
        },
      },
      scales: {
        x: { type: "logarithmic", ...axis("$ / 1M tokens (blended)") },
        y: axis("AA intelligence index"),
      },
    },
    plugins: [callouts],
  });

  const sp = document.getElementById("sparklines");
  for (const [mid, srcs] of Object.entries(trends)) {
    const series = srcs.artificialanalysis?.intelligence_index;
    if (!series || series.length < 2) continue;
    const wrap = document.createElement("div"); wrap.className = "spark";
    wrap.innerHTML = `<span>${esc(latest.models[mid]?.name ?? mid)}</span><canvas height="40"></canvas>`;
    sp.appendChild(wrap);
    new Chart(wrap.querySelector("canvas"), {
      type: "line",
      data: { labels: series.map(p => p[0]),
              datasets: [{ data: series.map(p => p[1]), borderColor: C.ink,
                           borderWidth: 1.5, pointRadius: 0, tension: 0.25 }] },
      options: { plugins: { legend: { display: false }, tooltip: { enabled: false } },
                 scales: { x: { display: false }, y: { display: false } } },
    });
  }
}

(async () => {
  const [latest, trends, sourcesDoc] = await Promise.all([
    loadJSON("data/latest.json"), loadJSON("data/trends.json"), loadJSON("data/sources.json")]);
  const okCount = Object.values(latest.sources).filter(s => s.ok).length;
  const total = Object.keys(latest.sources).length;
  document.getElementById("generated-at").textContent =
    `${okCount}/${total} sources live · updated ${latest.generated_at}`;
  renderChanges(latest.changes ?? [], latest.models);
  renderTable(latest);
  renderSources(sourcesDoc, latest);
  renderCharts(latest, trends);
})().catch(e => { document.body.insertAdjacentHTML("afterbegin",
  `<p class="error">Failed to load data: ${e.message}</p>`); });
