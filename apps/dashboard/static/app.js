const runButton = document.querySelector("#runBacktest");
const runButtonText = document.querySelector("#runButtonText");
const initialEquity = document.querySelector("#initialEquity");
const finalEquity = document.querySelector("#finalEquity");
const totalReturn = document.querySelector("#totalReturn");
const orderStats = document.querySelector("#orderStats");
const runFeedback = document.querySelector("#runFeedback");
const curveStatus = document.querySelector("#curveStatus");
const lastUpdated = document.querySelector("#lastUpdated");
const pendingStats = document.querySelector("#pendingStats");
const suggestionsTable = document.querySelector("#suggestionsTable");
const ordersTable = document.querySelector("#ordersTable");
const equityChart = document.querySelector("#equityChart");
const metrics = Array.from(document.querySelectorAll(".metric"));
const navLinks = Array.from(document.querySelectorAll(".nav-list a"));
const configInputs = {
  symbol: document.querySelector("#symbolInput"),
  shortWindow: document.querySelector("#shortWindowInput"),
  longWindow: document.querySelector("#longWindowInput"),
  targetWeight: document.querySelector("#targetWeightInput"),
  maxSymbolWeight: document.querySelector("#maxSymbolWeightInput"),
  maxOrderPct: document.querySelector("#maxOrderPctInput"),
  initialCash: document.querySelector("#initialCashInput"),
  commission: document.querySelector("#commissionInput"),
  slippage: document.querySelector("#slippageInput"),
  sampleDays: document.querySelector("#sampleDaysInput"),
  longOnly: document.querySelector("#longOnlyInput"),
};

let runCount = 0;
let pendingSuggestions = [];
let executionLog = [];

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

function formatPct(value) {
  return `${Number(value).toFixed(2)}%`;
}

async function runBacktest() {
  const startedAt = performance.now();
  const config = readConfig();
  const validationError = validateConfig(config);
  if (validationError) {
    showConfigError(validationError);
    return;
  }

  runButton.disabled = true;
  runButtonText.textContent = "运行中";
  curveStatus.textContent = "运行中";
  curveStatus.className = "status-chip running";
  runFeedback.textContent = "请求回测 API";
  finalEquity.textContent = "计算中";
  totalReturn.textContent = "--";
  orderStats.textContent = "--";
  equityChart.innerHTML = "";
  pendingStats.textContent = "--";
  suggestionsTable.innerHTML = '<tr><td colspan="7" class="empty">正在生成订单建议...</td></tr>';
  executionLog = [];
  renderOrders(executionLog);

  try {
    const payload = await requestBacktest(config);
    renderSummary(payload.summary);
    renderChart(payload.equity_curve);
    pendingSuggestions = payload.order_suggestions || [];
    renderSuggestions(pendingSuggestions);
    renderOrders(executionLog);
    runCount += 1;
    const elapsedMs = Math.max(1, Math.round(performance.now() - startedAt));
    curveStatus.textContent = `已完成 #${runCount}`;
    curveStatus.className = "status-chip complete";
    runFeedback.textContent = `${elapsedMs} ms`;
    lastUpdated.textContent = new Date().toLocaleString();
    pulseMetrics();
  } catch (error) {
    curveStatus.textContent = "失败";
    curveStatus.className = "status-chip";
    runFeedback.textContent = "请求失败";
    ordersTable.innerHTML = `<tr><td colspan="7" class="empty">${error.message}</td></tr>`;
  } finally {
    runButton.disabled = false;
    runButtonText.textContent = "重新运行";
  }
}

async function requestBacktest(config) {
  if (location.hostname.endsWith("github.io") || location.protocol === "file:") {
    return runStaticBacktest(config);
  }

  try {
    const response = await fetch("api/sample-backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
      cache: "no-store",
    });
    if (response.ok) {
      return await response.json();
    }
    if (response.status !== 404) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || `API returned ${response.status}`);
    }
  } catch (error) {
    if (!String(error.message).includes("Failed to fetch")) {
      throw error;
    }
  }

  return runStaticBacktest(config);
}

function readConfig() {
  return {
    symbol: configInputs.symbol.value.trim().toUpperCase(),
    short_window: Number(configInputs.shortWindow.value),
    long_window: Number(configInputs.longWindow.value),
    target_weight: Number(configInputs.targetWeight.value) / 100,
    max_symbol_weight: Number(configInputs.maxSymbolWeight.value) / 100,
    max_order_notional_pct: Number(configInputs.maxOrderPct.value) / 100,
    initial_cash: Number(configInputs.initialCash.value),
    commission_per_order: Number(configInputs.commission.value),
    slippage_bps: Number(configInputs.slippage.value),
    sample_days: Number(configInputs.sampleDays.value),
    long_only: configInputs.longOnly.checked,
  };
}

function validateConfig(config) {
  if (!config.symbol.match(/^[A-Z0-9]+$/)) {
    return "标的只能包含字母和数字";
  }
  if (config.short_window >= config.long_window) {
    return "短均线必须小于长均线";
  }
  if (config.long_window >= config.sample_days) {
    return "长均线必须小于样本天数";
  }
  if (config.target_weight > config.max_symbol_weight) {
    return "目标仓位不能超过单标的上限";
  }
  if (config.target_weight > config.max_order_notional_pct) {
    return "目标仓位不能超过单笔订单上限，否则第一笔建仓会被风控拦截";
  }
  return "";
}

function showConfigError(message) {
  curveStatus.textContent = "配置错误";
  curveStatus.className = "status-chip";
  runFeedback.textContent = message;
  suggestionsTable.innerHTML = `<tr><td colspan="7" class="empty">${message}</td></tr>`;
  focusSection(document.querySelector("#strategy"));
}

function renderSummary(summary) {
  initialEquity.textContent = currency.format(summary.initial_equity);
  finalEquity.textContent = currency.format(summary.final_equity);
  totalReturn.textContent = formatPct(summary.total_return_pct);
  orderStats.textContent = `${summary.orders} 建议`;
}

function runStaticBacktest(config) {
  const bars = generateStaticBars(config.symbol, config.sample_days);
  let cash = config.initial_cash;
  let quantity = 0;
  let pendingTargetWeight = null;
  const equityCurve = [];
  const orders = [];
  const fills = [];
  const closes = [];

  for (const bar of bars) {
    const price = bar.close;
    const equityBeforeTrade = cash + quantity * price;

    if (pendingTargetWeight !== null) {
      const targetQuantity = Math.floor((equityBeforeTrade * pendingTargetWeight) / price);
      const delta = targetQuantity - quantity;
      if (delta !== 0) {
        const side = delta > 0 ? "buy" : "sell";
        const orderQuantity = Math.abs(delta);
        const notional = orderQuantity * price;
        const projectedValue = side === "buy" ? quantity * price + notional : quantity * price - notional;
        let status = "filled";
        let rejectionReason = null;

        if (notional > equityBeforeTrade * config.max_order_notional_pct) {
          status = "rejected";
          rejectionReason = "order notional exceeds max order limit";
        } else if (projectedValue > equityBeforeTrade * config.max_symbol_weight) {
          status = "rejected";
          rejectionReason = "projected symbol weight exceeds max symbol limit";
        } else if (config.long_only && side === "sell" && orderQuantity > quantity) {
          status = "rejected";
          rejectionReason = "long-only mode cannot sell more than current position";
        }

        const order = {
          id: makeOrderId(orders.length),
          symbol: config.symbol,
          side,
          quantity: orderQuantity,
          estimated_price: round2(price),
          notional: round2(notional),
          status,
          reason: `${bar.date}: static MA signal`,
          rejection_reason: rejectionReason,
        };
        orders.push(order);

        if (status === "filled") {
          const fillPrice = side === "buy" ? price * (1 + config.slippage_bps / 10000) : price * (1 - config.slippage_bps / 10000);
          if (side === "buy") {
            cash -= orderQuantity * fillPrice + config.commission_per_order;
            quantity += orderQuantity;
          } else {
            cash += orderQuantity * fillPrice - config.commission_per_order;
            quantity -= orderQuantity;
          }
          fills.push({
            order_id: order.id,
            date: bar.date,
            symbol: config.symbol,
            side,
            quantity: orderQuantity,
            price: round2(fillPrice),
            commission: round2(config.commission_per_order),
            notional: round2(orderQuantity * fillPrice),
          });
        }
      }
    }

    closes.push(price);
    const equity = cash + quantity * price;
    equityCurve.push({
      date: bar.date,
      cash: round2(cash),
      market_value: round2(quantity * price),
      equity: round2(equity),
    });

    pendingTargetWeight = closes.length < config.long_window ? 0 : nextTargetWeight(closes, config);
  }

  const initialEquity = equityCurve.length ? equityCurve[0].equity : config.initial_cash;
  const finalEquity = equityCurve.length ? equityCurve[equityCurve.length - 1].equity : config.initial_cash;
  const orderSuggestions = orders
    .filter((order) => order.status !== "rejected")
    .slice(-10)
    .map((order) => ({
      ...order,
      status: "pending_confirmation",
      suggestion_id: `suggest-${order.id}`,
    }));

  return {
    mode: "static",
    config,
    summary: {
      initial_equity: round2(initialEquity),
      final_equity: round2(finalEquity),
      total_return_pct: round2(((finalEquity / initialEquity) - 1) * 100),
      orders: orders.length,
      fills: fills.length,
      rejected_orders: orders.filter((order) => order.status === "rejected").length,
    },
    equity_curve: equityCurve,
    order_suggestions: orderSuggestions,
    orders: orders.slice(-20),
    fills: fills.slice(-20),
  };
}

function generateStaticBars(symbol, days) {
  const bars = [];
  const current = new Date(Date.UTC(2024, 0, 2));
  let price = 100;

  while (bars.length < days) {
    const weekday = current.getUTCDay();
    if (weekday !== 0 && weekday !== 6) {
      const drift = bars.length < days * 0.65 ? 0.08 : -0.03;
      price = Math.max(1, price + drift);
      bars.push({
        symbol,
        date: current.toISOString().slice(0, 10),
        close: round2(price),
      });
    }
    current.setUTCDate(current.getUTCDate() + 1);
  }

  return bars;
}

function nextTargetWeight(closes, config) {
  const shortValues = closes.slice(-config.short_window);
  const longValues = closes.slice(-config.long_window);
  const shortMa = shortValues.reduce((sum, value) => sum + value, 0) / shortValues.length;
  const longMa = longValues.reduce((sum, value) => sum + value, 0) / longValues.length;
  return shortMa > longMa ? config.target_weight : 0;
}

function makeOrderId(index) {
  return `S${String(index + 1).padStart(7, "0")}`;
}

function round2(value) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function renderSuggestions(suggestions) {
  pendingStats.textContent = `${suggestions.length} 待确认`;
  if (!suggestions.length) {
    suggestionsTable.innerHTML = '<tr><td colspan="7" class="empty">当前策略没有生成订单建议</td></tr>';
    return;
  }

  suggestionsTable.innerHTML = suggestions
    .map(
      (order) => `
        <tr>
          <td>${order.id}</td>
          <td>${order.symbol}</td>
          <td class="${order.side}">${order.side.toUpperCase()}</td>
          <td>${order.quantity}</td>
          <td>${currency.format(order.estimated_price)}</td>
          <td>${currency.format(order.notional)}</td>
          <td>
            <span class="action-group">
              <button class="mini-button confirm" type="button" data-action="confirm" data-id="${order.suggestion_id}">确认</button>
              <button class="mini-button reject" type="button" data-action="reject" data-id="${order.suggestion_id}">拒绝</button>
            </span>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderOrders(orders) {
  if (!orders.length) {
    ordersTable.innerHTML = '<tr><td colspan="7" class="empty">确认或拒绝待确认订单后显示日志</td></tr>';
    return;
  }

  ordersTable.innerHTML = orders
    .map(
      (order) => `
        <tr>
          <td>${order.id}</td>
          <td>${order.symbol}</td>
          <td class="${order.side}">${order.side.toUpperCase()}</td>
          <td>${order.quantity}</td>
          <td>${currency.format(order.estimated_price)}</td>
          <td>${currency.format(order.notional)}</td>
          <td class="${order.statusClass || ""}">${order.status}</td>
        </tr>
      `,
    )
    .join("");
}

function handleSuggestionAction(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const action = button.dataset.action;
  const suggestionId = button.dataset.id;
  const suggestion = pendingSuggestions.find((order) => order.suggestion_id === suggestionId);
  if (!suggestion) {
    return;
  }

  pendingSuggestions = pendingSuggestions.filter((order) => order.suggestion_id !== suggestionId);
  const executedOrder = {
    ...suggestion,
    status: action === "confirm" ? "confirmed_paper" : "rejected_by_user",
    statusClass: action === "confirm" ? "status-confirmed" : "status-rejected",
  };
  executionLog = [executedOrder, ...executionLog];

  renderSuggestions(pendingSuggestions);
  renderOrders(executionLog);
  orderStats.textContent = `${pendingSuggestions.length} 待确认 / ${executionLog.length} 已处理`;
  lastUpdated.textContent = new Date().toLocaleString();
  focusSection(document.querySelector("#orders"));
}

function renderChart(points) {
  if (!points.length) {
    equityChart.innerHTML = "";
    return;
  }

  const width = 900;
  const height = 260;
  const pad = 34;
  const values = points.map((point) => point.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  const coordinates = points.map((point, index) => {
    const x = pad + (index / Math.max(points.length - 1, 1)) * (width - pad * 2);
    const y = height - pad - ((point.equity - min) / span) * (height - pad * 2);
    return [x, y];
  });

  const path = coordinates
    .map(([x, y], index) => `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`)
    .join(" ");
  const area = `${path} L ${coordinates[coordinates.length - 1][0].toFixed(2)} ${height - pad} L ${pad} ${height - pad} Z`;

  equityChart.innerHTML = `
    <defs>
      <linearGradient id="equityFill" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="#1f7a4d" stop-opacity="0.28"></stop>
        <stop offset="100%" stop-color="#1f7a4d" stop-opacity="0.02"></stop>
      </linearGradient>
    </defs>
    <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" stroke="#d7d1c4"></line>
    <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" stroke="#d7d1c4"></line>
    <path d="${area}" fill="url(#equityFill)"></path>
    <path d="${path}" fill="none" stroke="#1f7a4d" stroke-width="3" stroke-linejoin="round"></path>
    <circle cx="${coordinates[coordinates.length - 1][0]}" cy="${coordinates[coordinates.length - 1][1]}" r="5" fill="#171716"></circle>
    <text x="${pad}" y="22" fill="#6e6a61" font-size="12">${currency.format(max)}</text>
    <text x="${pad}" y="${height - 10}" fill="#6e6a61" font-size="12">${currency.format(min)}</text>
  `;
}

function pulseMetrics() {
  metrics.forEach((metric) => {
    metric.classList.remove("updated");
    void metric.offsetWidth;
    metric.classList.add("updated");
  });
}

function activateNav(hash) {
  navLinks.forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === hash);
  });
}

function focusSection(target) {
  target.classList.remove("section-focus");
  void target.offsetWidth;
  target.classList.add("section-focus");
  window.setTimeout(() => target.classList.remove("section-focus"), 950);
}

function handleNavClick(event) {
  const link = event.currentTarget;
  const hash = link.getAttribute("href");
  const target = document.querySelector(hash);
  if (!target) {
    return;
  }

  event.preventDefault();
  activateNav(hash);
  history.replaceState(null, "", hash);
  target.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
  focusSection(target);
}

navLinks.forEach((link) => link.addEventListener("click", handleNavClick));
activateNav(window.location.hash || "#overview");
suggestionsTable.addEventListener("click", handleSuggestionAction);
runButton.addEventListener("click", runBacktest);
