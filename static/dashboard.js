let equityChart = null;
let settingsCache = [];

const ZH = {
  unauthorized: "\u672a\u767b\u5f55",
  accountEquity: "\u8d26\u6237\u6743\u76ca",
  cash: "\u53ef\u7528\u73b0\u91d1",
  totalReturn: "\u603b\u6536\u76ca\u7387",
  scansToday: "\u4eca\u65e5\u626b\u63cf",
  signalsToday: "\u4eca\u65e5\u4fe1\u53f7",
  openPositions: "\u5f53\u524d\u6301\u4ed3",
  realizedToday: "\u4eca\u65e5\u5df2\u5b9e\u73b0",
  riskPct: "\u98ce\u9669\u6bd4\u4f8b",
  closedTrades: "\u5df2\u5e73\u4ed3\u7b14\u6570",
  winRate: "\u80dc\u7387",
  sharpe: "Sharpe",
  maxDrawdown: "\u6700\u5927\u56de\u64a4",
  profitFactor: "Profit Factor",
  turnover: "\u6362\u624b\u500d\u6570",
  breaker: "\u7194\u65ad\u72b6\u6001",
  breakerOn: "\u5df2\u89e6\u53d1",
  breakerOff: "\u6b63\u5e38",
  noData: "\u6682\u65e0\u6570\u636e",
  running: "\u8fd0\u884c\u4e2d",
  task: "\u4efb\u52a1",
  started: "\u5f00\u59cb",
  finished: "\u7ed3\u675f",
  code: "\u72b6\u6001\u7801",
  noTaskOutput: "\u6682\u65e0\u4efb\u52a1\u8f93\u51fa",
  yes: "\u662f",
  no: "\u5426",
  noComment: "\u6682\u65e0\u8bc4\u8bed",
  ok: "\u64cd\u4f5c\u6210\u529f",
  saved: "\u4fdd\u5b58\u6210\u529f",
};

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error(ZH.unauthorized);
  }
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status} ${txt}`);
  }
  return res.json();
}

function renderFundStats(metrics) {
  const risk = metrics.risk || {};
  const breakerOn = risk.can_open_new_positions === false;
  const items = [
    [ZH.closedTrades, String(metrics.closed_trades ?? 0), ""],
    [ZH.winRate, fmtPct(metrics.win_rate_pct ?? 0), (metrics.win_rate_pct ?? 0) >= 50 ? "good" : "bad"],
    [ZH.sharpe, Number(metrics.sharpe ?? 0).toFixed(2), (metrics.sharpe ?? 0) >= 1 ? "good" : "bad"],
    [ZH.maxDrawdown, fmtPct(metrics.max_drawdown_pct ?? 0), (metrics.max_drawdown_pct ?? 0) <= 12 ? "good" : "bad"],
    [ZH.profitFactor, Number(metrics.profit_factor ?? 0).toFixed(2), (metrics.profit_factor ?? 0) >= 1.2 ? "good" : "bad"],
    [ZH.turnover, `${Number(metrics.turnover_x ?? 0).toFixed(2)}x`, ""],
    [ZH.breaker, breakerOn ? ZH.breakerOn : ZH.breakerOff, breakerOn ? "bad" : "good"],
  ];
  const host = document.getElementById("fundStats");
  host.innerHTML = items.map(([label, value, cls]) => `
    <article class="card stat">
      <div class="label">${label}</div>
      <div class="value ${cls}">${value}</div>
    </article>
  `).join("");
}

function fmtMoney(v) {
  return `$${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function fmtPct(v) {
  return `${Number(v || 0).toFixed(2)}%`;
}

function renderStats(summary) {
  const items = [
    [ZH.accountEquity, fmtMoney(summary.equity), summary.total_return_pct >= 0 ? "good" : "bad"],
    [ZH.cash, fmtMoney(summary.cash), ""],
    [ZH.totalReturn, fmtPct(summary.total_return_pct), summary.total_return_pct >= 0 ? "good" : "bad"],
    [ZH.scansToday, String(summary.today_scans), ""],
    [ZH.signalsToday, String(summary.today_signals), ""],
    [ZH.openPositions, String(summary.open_positions), ""],
    [ZH.realizedToday, fmtMoney(summary.realized_pnl_today), summary.realized_pnl_today >= 0 ? "good" : "bad"],
    [ZH.riskPct, fmtPct(summary.risk_pct * 100), ""],
  ];
  const host = document.getElementById("stats");
  host.innerHTML = items.map(([label, value, cls]) => `
    <article class="card stat">
      <div class="label">${label}</div>
      <div class="value ${cls}">${value}</div>
    </article>
  `).join("");
}

function fillTable(tableId, rows, mapper, emptyColspan = 8) {
  const body = document.querySelector(`#${tableId} tbody`);
  body.innerHTML = rows.map(mapper).join("") || `<tr><td colspan="${emptyColspan}">${ZH.noData}</td></tr>`;
}

function renderEquity(points) {
  const ctx = document.getElementById("equityChart");
  const labels = points.map((p, idx) => (idx % 6 === 0 ? p.ts.slice(5, 16) : ""));
  const values = points.map(p => p.equity);
  if (equityChart) {
    equityChart.data.labels = labels;
    equityChart.data.datasets[0].data = values;
    equityChart.update();
    return;
  }
  equityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "\u6743\u76ca",
        data: values,
        borderColor: "#1f6feb",
        backgroundColor: "rgba(31, 111, 235, 0.12)",
        fill: true,
        borderWidth: 2,
        tension: 0.2,
        pointRadius: 0,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8 } },
        y: { ticks: { callback: (v) => `$${Number(v).toLocaleString()}` } },
      },
    },
  });
}

function renderTask(task) {
  const host = document.getElementById("taskBox");
  const lines = [
    `${ZH.running}: ${task.running ? ZH.yes : ZH.no}`,
    `${ZH.task}: ${task.name || "-"}`,
    `${ZH.started}: ${task.started_at || "-"}`,
    `${ZH.finished}: ${task.finished_at || "-"}`,
    `${ZH.code}: ${task.return_code ?? "-"}`,
    "",
    task.output_tail || ZH.noTaskOutput,
  ];
  host.textContent = lines.join("\n");
}

function renderDailyComment(payload) {
  const host = document.getElementById("dailyComment");
  host.textContent = `${payload.date}\n\n${payload.comment || ZH.noComment}`;
}

function renderSettings(settings) {
  settingsCache = settings;
  const host = document.getElementById("settingsForm");
  host.innerHTML = settings.map((s) => {
    if (s.type === "bool") {
      return `
        <div class="setting-item">
          <label for="setting-${s.key}">${s.label}</label>
          <input id="setting-${s.key}" data-key="${s.key}" data-type="${s.type}" type="checkbox" ${s.value ? "checked" : ""} />
        </div>
      `;
    }
    const step = s.type === "int" ? "1" : "0.0001";
    return `
      <div class="setting-item">
        <label for="setting-${s.key}">${s.label}</label>
        <input id="setting-${s.key}" data-key="${s.key}" data-type="${s.type}" type="${s.type === "str" ? "text" : "number"}" step="${step}" value="${s.value ?? ""}" />
      </div>
    `;
  }).join("");
}

function collectSettingsPayload() {
  const payload = {};
  for (const s of settingsCache) {
    const el = document.querySelector(`#setting-${s.key}`);
    if (!el) continue;
    if (s.type === "bool") payload[s.key] = el.checked;
    else if (s.type === "int") payload[s.key] = Number.parseInt(el.value, 10);
    else if (s.type === "float") payload[s.key] = Number.parseFloat(el.value);
    else payload[s.key] = el.value.trim();
  }
  return payload;
}

async function refreshAll() {
  const [summary, equity, positions, signals, orders, task, settings, dailyComment, fundMetrics] = await Promise.all([
    fetchJson("/api/summary"),
    fetchJson("/api/equity"),
    fetchJson("/api/positions"),
    fetchJson("/api/signals"),
    fetchJson("/api/orders"),
    fetchJson("/api/task"),
    fetchJson("/api/settings"),
    fetchJson("/api/daily-comment"),
    fetchJson("/api/fund-metrics"),
  ]);
  renderStats(summary);
  renderFundStats(fundMetrics);
  renderEquity(equity);
  renderTask(task);
  renderSettings(settings);
  renderDailyComment(dailyComment);

  fillTable("positionsTable", positions, (r) => `
    <tr>
      <td>${r.symbol}</td>
      <td>${r.qty}</td>
      <td>${fmtMoney(r.avg_cost)}</td>
      <td>${r.last_price ? fmtMoney(r.last_price) : "-"}</td>
      <td class="${r.unrealized >= 0 ? "good" : "bad"}">${fmtMoney(r.unrealized)} (${fmtPct(r.unrealized_pct)})</td>
      <td>${r.updated_at}</td>
    </tr>
  `, 6);

  fillTable("signalsTable", signals, (r) => `
    <tr>
      <td>${r.date}</td>
      <td>${r.stock}</td>
      <td>${fmtMoney(r.last_price)}</td>
      <td>${r.trend}</td>
      <td>${r.ob_signal}</td>
    </tr>
  `, 5);

  fillTable("ordersTable", orders, (r) => `
    <tr>
      <td>${r.ts}</td>
      <td>${r.symbol}</td>
      <td>${r.action}</td>
      <td>${r.qty}</td>
      <td>${fmtMoney(r.price)}</td>
      <td class="${r.realized_pnl >= 0 ? "good" : "bad"}">${fmtMoney(r.realized_pnl)}</td>
      <td>${r.reason}</td>
    </tr>
  `, 7);
}

async function runTask(url) {
  try {
    const data = await fetchJson(url, { method: "POST" });
    alert(data.message || ZH.ok);
    await refreshAll();
  } catch (err) {
    alert(err.message);
  }
}

async function saveSettings() {
  try {
    const payload = collectSettingsPayload();
    const data = await fetchJson("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    alert(data.message || ZH.saved);
    await refreshAll();
  } catch (err) {
    alert(err.message);
  }
}

document.getElementById("runScan").addEventListener("click", () => runTask("/api/run/scan"));
document.getElementById("runReview").addEventListener("click", () => runTask("/api/run/review"));
document.getElementById("sendTelegram").addEventListener("click", () => runTask("/api/run/telegram"));
document.getElementById("saveSettings").addEventListener("click", saveSettings);

refreshAll().catch(console.error);
setInterval(() => refreshAll().catch(console.error), 10000);
