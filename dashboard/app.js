(function () {
  "use strict";

  const THEME_KEY = "ultron_training_theme";
  const RAM_LIMIT_KEY = "ultron_training_ram_limit_gb";
  let chartDrawPending = false;

  const $ = function (id) { return document.getElementById(id); };
  const state = {
    servers: [],
    currentView: "overview",
    projectConfig: {},
    ramLimitGb: 6,
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
      return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char];
    });
  }

  function showNotice(message, kind) {
    const box = $("globalNotice");
    if (!box) return;
    box.textContent = message;
    box.className = "notice" + (kind ? " notice-" + kind : "");
    box.hidden = !message;
  }

  function setConnection(label, kind) {
    const badge = $("connectionBadge");
    badge.textContent = label;
    badge.className = "connection-badge" + (kind ? " " + kind : "");
    $("footerConnection").textContent = "PUBLIC DASHBOARD";
  }

  async function loadServerRegistry() {
    try {
      const response = await fetch("../servers.json", {cache: "no-store"});
      if (!response.ok) throw new Error("Could not load servers.json.");
      const data = await response.json();
      state.servers = (data.servers || []).filter(function (server) { return server.enabled !== false; }).sort(function (a, b) {
        return Number(a.order || 999) - Number(b.order || 999);
      });
      const configResponse = await fetch("../config.json", {cache: "no-store"});
      if (configResponse.ok) state.projectConfig = await configResponse.json();
    } catch (error) {
      state.servers = [];
      showNotice("Server registry unavailable: " + error.message, "warn");
    }
  }

  function formatNumber(value, digits) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    return number.toLocaleString(undefined, {maximumFractionDigits: digits == null ? 2 : digits});
  }

  function quotaLimitHours(server) {
    const limits = server.limits || {};
    const period = limits.quota_period;
    if (period === "weekly") return Number(limits.weekly_gpu_hours_baseline || 0) || null;
    if (period === "monthly") return Number(limits.monthly_gpu_hours || 0) || null;
    return null;
  }

  function quotaUsage(server) {
    const limit = quotaLimitHours(server);
    const period = (server.limits || {}).quota_period;
    return {
      used: null,
      limit: limit,
      percent: null,
      label: period === "initial_credits_not_monthly"
        ? "One-time credits · usage not measured"
        : limit ? formatNumber(limit, 0) + " GPU hours published · usage not measured" : "Usage not published"
    };
  }

  function serverState(server) {
    const status = server.current_status || "unknown";
    if (status === "unavailable_until" && server.unavailable_until &&
        new Date(server.unavailable_until).getTime() <= Date.now()) return "unknown";
    if (status === "kicked_out" && server.kicked_out_until &&
        new Date(server.kicked_out_until).getTime() <= Date.now()) return "unknown";
    return status;
  }

  function renderNextAction() {
    $("nextActionTitle").textContent = "ULTRON is not training";
    $("nextActionText").textContent = "This account-free website provides the public mathematics-learning interface and provider information. It cannot access personal history, checkpoints or remote execution controls.";
    $("nextActionMeta").textContent = "Public browser access · neural model untrained · training disabled";
    $("nextServerButton").hidden = true;
  }

  function renderMetrics() {
    $("metricState").textContent = "UNTRAINED";
    $("metricStateDetail").textContent = "No neural weights have been trained";
    $("metricStep").textContent = "AVAILABLE";
    $("metricTopic").textContent = "Deterministic foundation solver";
    $("metricLoss").textContent = "LIMITED";
    $("metricTimeLeft").textContent = "DISABLED";
    $("metricSessionAge").textContent = "No training run is authorized";
    $("heartbeatAge").textContent = "DISABLED";
    $("checkpointAge").textContent = "NOT USED";
    $("activeServer").textContent = "NOT CONNECTED";
    $("leaseState").textContent = "NOT REQUIRED";
  }

  function renderMastery() {
    $("masteryCount").textContent = "Not available";
    $("masteryList").innerHTML = '<p class="empty-state">Training evaluation data is unavailable because the neural model has not been trained.</p>';
  }

  function scheduleChartDraw() {
    if (document.hidden || state.currentView !== "overview" || chartDrawPending) return;
    chartDrawPending = true;
    ULTRON_RUNTIME.scheduleFrame(function () {
      chartDrawPending = false;
      if (!document.hidden && state.currentView === "overview") drawChart();
    }, window);
  }

  function drawChart() {
    if (document.hidden || state.currentView !== "overview") return;
    const canvas = $("lossChart");
    if (!canvas) return;
    let context = null;
    try { context = canvas.getContext("2d"); } catch (_) { return; }
    if (!context || typeof context.setTransform !== "function") return;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(280, Math.floor(rect.width || 600));
    const height = 190;
    const ratio = window.devicePixelRatio || 1;
    const pixelWidth = Math.round(width * ratio);
    const pixelHeight = Math.round(height * ratio);
    if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
    if (canvas.height !== pixelHeight) canvas.height = pixelHeight;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);
    const points = [];
    if (points.length < 2) {
      context.fillStyle = getComputedStyle(document.body).getPropertyValue("--muted");
      context.font = "12px system-ui";
      context.fillText("Loss history will appear after heartbeats.", 12, 95);
      $("chartFirst").textContent = points.length ? "1 data point" : "Waiting for data";
      $("chartLast").textContent = "—";
      return;
    }
    const values = points.map(function (point) { return Number(point.loss); });
    const min = Math.min.apply(null, values);
    const max = Math.max.apply(null, values);
    const span = Math.max(0.000001, max - min);
    const padX = 12, padY = 16, chartW = width - 24, chartH = height - 32;
    const line = getComputedStyle(document.body).getPropertyValue("--red").trim() || "#ff3048";
    const grid = getComputedStyle(document.body).getPropertyValue("--line").trim() || "rgba(255,255,255,.1)";
    context.strokeStyle = grid;
    context.lineWidth = 1;
    for (let i = 0; i < 4; i++) {
      const y = padY + chartH * i / 3;
      context.beginPath(); context.moveTo(padX, y); context.lineTo(width - padX, y); context.stroke();
    }
    context.strokeStyle = line;
    context.lineWidth = 2.5;
    context.beginPath();
    values.forEach(function (value, index) {
      const x = padX + chartW * index / (values.length - 1);
      const y = padY + chartH * (1 - (value - min) / span);
      if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
    });
    context.stroke();
    context.fillStyle = line;
    const lastX = padX + chartW;
    const lastY = padY + chartH * (1 - (values[values.length - 1] - min) / span);
    context.beginPath(); context.arc(lastX, lastY, 4, 0, Math.PI * 2); context.fill();
    $("chartFirst").textContent = "Step " + formatNumber(points[0].step, 0) + " · " + formatNumber(values[0], 4);
    $("chartLast").textContent = "Step " + formatNumber(points[points.length - 1].step, 0) + " · " + formatNumber(values[values.length - 1], 4);
  }

  function renderServers() {
    const container = $("serverList");
    const nextId = null;
    if (!state.servers.length) {
      container.innerHTML = '<div class="empty-state panel">Could not load servers.json.</div>';
      return;
    }
    container.innerHTML = state.servers.map(function (server, index) {
      const status = serverState(server);
      const quota = quotaUsage(server);
      const quotaText = quota.percent == null ? quota.label : quota.label + " · " + formatNumber(quota.percent, 0) + "%" + (quota.percent >= 80 ? " · WARNING" : "");
      const startUrl = server.notebook_open_url || server.notebook_url || server.documentation_url || "#";
      const limitHours = server.limits && (server.limits.session_limit_hours || server.limits.free_studio_restart_hours || server.limits.job_execution_limit_hours || server.limits.session_hours);
      const limitText = limitHours ? limitHours + (server.limits.job_execution_limit_hours ? "h job" : "h session") : "Session varies";
      return '<article class="server-card' + (server.id === nextId ? ' next-server' : '') + '">' +
        '<div class="server-main">' +
          '<div class="server-title-row"><span class="server-number">0' + (index + 1) + '</span><strong class="server-title">' + escapeHtml(server.name) + '</strong><span class="status-pill ' + escapeHtml(status) + '">' + escapeHtml(status.replace(/_/g, " ")) + '</span>' + (server.id === nextId ? '<span class="next-flag">NEXT</span>' : '') + '</div>' +
          '<div class="server-sub">' + escapeHtml(server.role || "compute server") + ' · ' + escapeHtml(limitText) + ' · Provider automation: not controlled by this dashboard</div>' +
          '<div class="server-meta"><span class="meta-chip">' + escapeHtml(server.hardware && (server.hardware.cpu_only ? "CPU" : server.hardware.free_gpu_options ? "GPU / CPU" : server.hardware.preferred || "Compute")) + '</span><span class="meta-chip">' + escapeHtml(quotaText) + '</span><span class="meta-chip">Order ' + escapeHtml(server.order) + '</span></div>' +
          '<div class="quota-line"><div class="quota-top"><span>Quota usage</span><span>' + escapeHtml(quota.percent == null ? "Not measurable" : formatNumber(quota.percent, 1) + "%") + '</span></div><div class="quota-track"><div class="quota-fill" style="width:' + (quota.percent == null ? 0 : Math.max(0, Math.min(100, quota.percent))) + '%"></div></div></div>' +
          '<div class="server-sub">' + escapeHtml(server.status_reason || server.limits && server.limits.quota_notes || "") + '</div>' +
        '</div>' +
          '<div class="server-actions"><a class="secondary-button button-link" href="' + escapeHtml(startUrl) + '" target="_blank" rel="noopener">Open provider ↗</a></div>' +
      '</article>';
    }).join("");
  }

  function renderSettings() {
    const ramSlider = $("ramLimitSlider");
    if (ramSlider) {
      ramSlider.value = String(state.ramLimitGb);
      $("ramLimitValue").textContent = state.ramLimitGb + " GB";
      $("ramLimitStatus").textContent = "Saved in this browser only. This preference is not connected to remote training or hosted-runner memory controls.";
    }
    const review = state.projectConfig.terms_review || {};
    const intervalDays = Number(review.reminder_interval_days || 90);
    const lastReview = review.last_reviewed_date || "2026-11-17";
    const lastDate = new Date(lastReview + "T00:00:00Z");
    const dueDate = new Date(lastDate.getTime() + intervalDays * 86400000);
    const overdue = Date.now() >= dueDate.getTime();
    $("termsReviewStatus").textContent = overdue
      ? "Terms review is due. Last reviewed " + lastReview + "; please re-check the provider links below."
      : "Last reviewed " + lastReview + ". Next review due " + dueDate.toISOString().slice(0,10) + ".";
    $("termsLinks").innerHTML = state.servers.map(function (server) {
      const url = server.terms_url || server.documentation_url;
      if (!url) return "";
      return '<a href="' + escapeHtml(url) + '" target="_blank" rel="noopener">' + escapeHtml(server.name) + ' terms / docs ↗</a>';
    }).join("");
  }

  function renderAll() {
    renderNextAction();
    renderMetrics();
    renderMastery();
    scheduleChartDraw();
    renderServers();
    renderSettings();
  }

  function switchView(view) {
    state.currentView = view;
    document.querySelectorAll(".view-section").forEach(function (section) {
      section.hidden = section.id !== "view-" + view;
    });
    document.querySelectorAll(".nav-button").forEach(function (button) {
      const selected = button.getAttribute("data-view") === view;
      button.classList.toggle("active", selected);
      if (selected) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    const labels = {
      overview: ["OVERVIEW", "System overview"],
      learning: ["HOW ULTRON LEARNS", "Learning system"],
      servers: ["SERVERS", "Free compute servers"],
      math: ["MATH AGENT", "Solve mathematics"],
      settings: ["SETTINGS", "System settings"],
    };
    if (!labels[view]) return;
    $("viewName").textContent = labels[view][0];
    $("pageTitle").textContent = labels[view][1];
    if (view === "overview") scheduleChartDraw();
  }

  function applyTheme(theme) {
    document.body.setAttribute("data-theme", theme);
    try { localStorage.setItem(THEME_KEY, theme); } catch (_) {}
  }

  function initTheme() {
    let theme = "dark";
    try { theme = localStorage.getItem(THEME_KEY) || "dark"; } catch (_) {}
    applyTheme(theme === "light" ? "light" : "dark");
  }

  function bindEvents() {
    $("themeToggle").addEventListener("click", function () {
      applyTheme(document.body.getAttribute("data-theme") === "dark" ? "light" : "dark");
      scheduleChartDraw();
    });
    $("refreshButton").addEventListener("click", function () {
      loadServerRegistry().then(renderAll).catch(function (error) {
        showNotice("Server registry refresh failed: " + error.message, "warn");
      });
    });
    document.querySelectorAll("[data-view]").forEach(function (button) {
      button.addEventListener("click", function () { switchView(button.getAttribute("data-view")); });
    });
    $("ramLimitSlider").addEventListener("input", function () {
      const selected = Math.max(2, Math.min(10, Number($("ramLimitSlider").value)));
      state.ramLimitGb = Math.round(selected * 2) / 2;
      $("ramLimitValue").textContent = state.ramLimitGb + " GB";
      try { localStorage.setItem(RAM_LIMIT_KEY, String(state.ramLimitGb)); } catch (_) {}
      $("ramLimitStatus").textContent = "Saved as " + state.ramLimitGb + " GB in this browser only. It is not sent to a remote training process and does not cap hosted-runner memory.";
    });


    window.addEventListener("resize", scheduleChartDraw);
    if (typeof ResizeObserver === "function") {
      const chart = $("lossChart");
      if (chart && chart.parentElement) {
        const observer = new ResizeObserver(scheduleChartDraw);
        observer.observe(chart.parentElement);
      }
    }
  }

  function clearLegacyOwnerState() {
    // Remove stale credentials and account-specific caches from older builds once.
    // The public dashboard never restores, creates or refreshes an owner session.
    try { sessionStorage.removeItem("ultron_training_session"); } catch (_) {}
    try {
      for (let index = localStorage.length - 1; index >= 0; index -= 1) {
        const key = localStorage.key(index);
        if (key && key.indexOf("ultron_training_cache_") === 0) localStorage.removeItem(key);
      }
    } catch (_) {}
  }

  async function init() {
    initTheme();
    try {
      const savedRamLimit = Number(localStorage.getItem(RAM_LIMIT_KEY));
      if (Number.isFinite(savedRamLimit) && savedRamLimit >= 2 && savedRamLimit <= 10 && savedRamLimit * 2 === Math.round(savedRamLimit * 2)) {
        state.ramLimitGb = savedRamLimit;
      }
    } catch (_) {}
    bindEvents();
    await loadServerRegistry();
    clearLegacyOwnerState();
    setConnection("PUBLIC", "");
    $("lastUpdated").textContent = "Public browser mode · no account-specific data";
    showNotice("ULTRON is available without an account. This website does not load personal training history or checkpoints, and it cannot launch remote execution. The RAM slider is a browser-local preference only. Actual training remains disabled.", "info");
    renderAll();
  }

  document.addEventListener("DOMContentLoaded", init);
})();