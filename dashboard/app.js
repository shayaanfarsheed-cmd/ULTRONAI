(function () {
  "use strict";

  const CONFIG = window.ULTRON_CONFIG || {};
  const SUPABASE_URL = String(CONFIG.supabaseUrl || "").replace(/\/$/, "");
  const PUBLISHABLE_KEY = String(CONFIG.supabasePublishableKey || "");
  const OWNER_USER_ID = String(CONFIG.ownerUserId || "").trim();
  const API_ROOT = SUPABASE_URL + "/rest/v1/";
  const AUTH_ROOT = SUPABASE_URL + "/auth/v1/";
  const STORAGE_ROOT = SUPABASE_URL + "/storage/v1/";
  const SESSION_KEY = "ultron_training_session";
  const CACHE_PREFIX = "ultron_training_cache_";
  const THEME_KEY = "ultron_training_theme";
  const RAM_LIMIT_KEY = "ultron_training_ram_limit_gb";
  const POLL_MS = 15000;
  const STALE_SECONDS = 720;
  let sessionRefreshPromise = null;
  const runSessionRefresh = ULTRON_RUNTIME.createSingleFlight();
  let chartDrawPending = false;

  const $ = function (id) { return document.getElementById(id); };
  const state = {
    publicMode: true,
    authGeneration: 0,
    session: null,
    user: null,
    status: null,
    logs: [],
    switches: [],
    servers: [],
    checkpoints: [],
    dataFiles: [],
    dataLibraryBusy: false,
    askBusy: false,
    currentView: "overview",
    lastUpdated: null,
    stale: false,
    refreshing: false,
    checkpointBusy: false,
    quota: {},
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

  function showCheckpointNotice(message, kind) {
    const box = $("checkpointMessage");
    if (!box) return;
    box.textContent = message;
    box.className = "notice" + (kind ? " notice-" + kind : "");
    box.hidden = !message;
  }

  function setConnection(label, kind) {
    const badge = $("connectionBadge");
    badge.textContent = label;
    badge.className = "connection-badge" + (kind ? " " + kind : "");
    $("footerConnection").textContent = kind === "stale" ? "PUBLIC STATUS · OUT OF DATE" : "PUBLIC DASHBOARD";
  }

  function isConfigured() {
    return Boolean(SUPABASE_URL && PUBLISHABLE_KEY && PUBLISHABLE_KEY !== "sb_publishable_REPLACE_WITH_YOUR_KEY");
  }

  function loadSavedSession() {
    try {
      const value = sessionStorage.getItem(SESSION_KEY);
      return value ? JSON.parse(value) : null;
    } catch (_) {
      return null;
    }
  }

  function saveSession(session) {
    if (!session) {
      const previousUserId = state.user && state.user.id;
      state.session = null;
      state.user = null;
      try { sessionStorage.removeItem(SESSION_KEY); } catch (_) {}
      if (previousUserId) {
        try { localStorage.removeItem(CACHE_PREFIX + previousUserId); } catch (_) {}
      }
      return;
    }
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } catch (_) {
      state.session = null;
      state.user = null;
      try { sessionStorage.removeItem(SESSION_KEY); } catch (_) {}
      throw new Error("This browser cannot retain the sign-in session. Enable session storage or use Guest Mode.");
    }
    state.session = session;
    state.user = session.user || null;
  }

  function hasVerifiedOwnerSession() {
    return Boolean(!state.publicMode && OWNER_USER_ID && state.session &&
      state.session.access_token && state.user && state.user.id === OWNER_USER_ID &&
      state.session.user && state.session.user.id === OWNER_USER_ID);
  }

  function assertOwnerAccess(session) {
    if (!hasVerifiedOwnerSession() || (session && (!session.user || session.user.id !== OWNER_USER_ID))) {
      throw new Error("Owner access is required for this private operation.");
    }
  }

  function setAccessMode(isOwner) {
    const nextPublicMode = !isOwner;
    if (state.publicMode !== nextPublicMode) {
      state.authGeneration += 1;
      sessionRefreshPromise = null;
      runSessionRefresh.reset();
    }
    state.publicMode = nextPublicMode;
    if (!isOwner) {
      const previousUserId = state.user && state.user.id;
      if (previousUserId) {
        try { localStorage.removeItem(CACHE_PREFIX + previousUserId); } catch (_) {}
      }
      state.session = null;
      state.user = null;
      try { sessionStorage.removeItem(SESSION_KEY); } catch (_) {}
      state.status = null;
      state.logs = [];
      state.switches = [];
      state.checkpoints = [];
      state.dataFiles = [];
      state.quota = {};
      state.lastUpdated = null;
      state.stale = false;
    }
    const signIn = $("ownerSignInButton");
    const signOut = $("ownerSignOutButton");
    const account = document.querySelector(".account-email");
    if (signIn) signIn.hidden = Boolean(isOwner);
    if (signOut) signOut.hidden = !isOwner;
    if (account) account.textContent = isOwner ? "OWNER MODE" : "GUEST MODE";
    setConnection(isOwner ? "OWNER" : "GUEST MODE", isOwner ? "connected" : "");
    renderAll();
  }

  async function verifyOwnerSession() {
    if (!state.session || !state.session.access_token) return false;
    if (!OWNER_USER_ID) { saveSession(null); return false; }
    try {
      const session = await ensureSession();
      const response = await fetch(AUTH_ROOT + "user", {
        headers: {"apikey": PUBLISHABLE_KEY, "Authorization": "Bearer " + session.access_token}
      });
      const user = await response.json().catch(function () { return {}; });
      if (!response.ok || !user.id || user.id !== OWNER_USER_ID) {
        saveSession(null);
        return false;
      }
      saveSession(Object.assign({}, session, {user: user}));
      return true;
    } catch (_) {
      saveSession(null);
      return false;
    }
  }

  function showAuthMessage(message, kind) {
    const box = $("ownerAuthMessage");
    if (!box) return;
    box.textContent = message;
    box.className = "notice" + (kind ? " notice-" + kind : "");
    box.hidden = !message;
  }

  async function signInOwner(event) {
    event.preventDefault();
    const submit = $("ownerSubmitButton");
    const passwordInput = $("ownerPassword");
    const password = passwordInput.value;
    passwordInput.value = "";
    if (!isConfigured()) {
      showAuthMessage("Authentication is not configured yet. Guest Mode remains available.", "warn");
      return;
    }
    if (!OWNER_USER_ID) {
      showAuthMessage("Owner verification is not configured. Sign-in is safely disabled.", "warn");
      return;
    }
    const email = $("ownerEmail").value.trim();
    if (!email || !password) {
      showAuthMessage("Enter the owner email and password.", "error");
      return;
    }
    submit.disabled = true;
    showAuthMessage("Verifying owner credentials…", "");
    try {
      const data = await authRequest("token?grant_type=password", {email: email, password: password});
      const next = sessionFromResponse(data);
      if (!next.access_token || !next.refresh_token || !next.user || next.user.id !== OWNER_USER_ID) {
        if (next.access_token) {
          await fetch(AUTH_ROOT + "logout", {method: "POST", headers: {"apikey": PUBLISHABLE_KEY, "Authorization": "Bearer " + next.access_token}}).catch(function () {});
        }
        throw new Error("This account is not the configured ULTRON owner account.");
      }
      saveSession(next);
      setAccessMode(true);
      $("ownerPassword").value = "";
      $("ownerSignInDialog").close();
      showNotice("Owner session verified. Private data requests use the authenticated session.", "success");
      await refreshData();
      if (state.currentView === "data") await loadDataLibrary();
    } catch (error) {
      saveSession(null);
      setAccessMode(false);
      showAuthMessage(error.message || "Owner sign-in failed.", "error");
    } finally {
      passwordInput.value = "";
      submit.disabled = false;
    }
  }

  async function signOutOwner() {
    const session = state.session;
    const ownerId = state.user && state.user.id;
    if (ownerId) {
      try { localStorage.removeItem(CACHE_PREFIX + ownerId); } catch (_) {}
    }
    saveSession(null);
    setAccessMode(false);
    showNotice("Signed out locally. You are now using Guest Mode.", "info");
    if (session && session.access_token && isConfigured()) {
      try {
        const response = await fetch(AUTH_ROOT + "logout", {
          method: "POST",
          headers: {"apikey": PUBLISHABLE_KEY, "Authorization": "Bearer " + session.access_token}
        });
        if (!response.ok) throw new Error("Server sign-out could not be confirmed.");
      } catch (_) {
        showNotice("Guest Mode is active and local private data is cleared. Server-side sign-out could not be confirmed; the session token was discarded in this browser.", "warn");
      }
    }
  }

  function sessionFromResponse(data) {
    const expiresIn = Number(data.expires_in || 3600);
    const expiresAt = data.expires_at ? Number(data.expires_at) * 1000 : Date.now() + expiresIn * 1000;
    return {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      expires_at: expiresAt,
      token_type: data.token_type || "bearer",
      user: data.user || (state.session && state.session.user) || null
    };
  }

  async function authRequest(path, body) {
    const response = await fetch(AUTH_ROOT + path, {
      method: "POST",
      headers: {
        "apikey": PUBLISHABLE_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body || {})
    });
    const data = await response.json().catch(function () { return {}; });
    if (!response.ok) throw new Error(data.msg || data.message || data.error_description || data.error || "Authentication request failed (" + response.status + ").");
    return data;
  }

  function expireOwnerSession() {
    saveSession(null);
    if (!state.publicMode) setAccessMode(false);
  }

  async function ensureSession() {
    if (!state.session || !state.session.access_token) throw new Error("Please sign in again.");
    if (Number(state.session.expires_at || 0) > Date.now() + 60000) return state.session;
    if (!state.session.refresh_token) {
      expireOwnerSession();
      throw new Error("Your login expired. Please sign in again.");
    }
    if (sessionRefreshPromise) return sessionRefreshPromise;

    const refreshToken = state.session.refresh_token;
    const generation = state.authGeneration;
    const refreshPromise = runSessionRefresh(async function () {
      try {
        const data = await authRequest("token?grant_type=refresh_token", {refresh_token: refreshToken});
        const next = sessionFromResponse(data);
        if (generation !== state.authGeneration || !state.session ||
            state.session.refresh_token !== refreshToken) {
          throw new Error("The owner session changed while its token was refreshing.");
        }
        saveSession(next);
        return next;
      } catch (_) {
        if (generation === state.authGeneration && state.session &&
            state.session.refresh_token === refreshToken) {
          expireOwnerSession();
        }
        throw new Error("Your owner session expired. Please sign in again.");
      }
    });
    sessionRefreshPromise = refreshPromise;
    try {
      return await refreshPromise;
    } finally {
      if (sessionRefreshPromise === refreshPromise) sessionRefreshPromise = null;
    }
  }

  async function apiRequest(table, method, query, body) {
    const session = await ensureSession();
    assertOwnerAccess(session);
    const url = API_ROOT + table + (query ? "?" + query : "");
    const headers = {
      "apikey": PUBLISHABLE_KEY,
      "Authorization": "Bearer " + session.access_token,
      "Accept-Profile": "training_api"
    };
    if (method !== "GET" && method !== "HEAD") {
      headers["Content-Profile"] = "training_api";
      headers["Content-Type"] = "application/json";
      headers["Prefer"] = "return=representation";
    }
    const response = await fetch(url, {
      method: method,
      headers: headers,
      body: body == null ? undefined : JSON.stringify(body)
    });
    const raw = await response.text();
    const data = raw ? (function () { try { return JSON.parse(raw); } catch (_) { return raw; } })() : null;
    if (!response.ok) {
      if (response.status === 401) {
        expireOwnerSession();
      }
      const message = data && (data.message || data.hint || data.error) ? (data.message || data.hint || data.error) : "Database request failed (" + response.status + ").";
      throw new Error(message);
    }
    return data;
  }

  async function storageRequest(path, method, body, binary, maxBytes) {
    const session = await ensureSession();
    assertOwnerAccess(session);
    const headers = {
      "apikey": PUBLISHABLE_KEY,
      "Authorization": "Bearer " + session.access_token
    };
    if (body != null && !(body instanceof Blob) && !(body instanceof ArrayBuffer)) {
      headers["Content-Type"] = "application/json";
    }
    const response = await fetch(STORAGE_ROOT + path, {
      method: method || "GET",
      headers: headers,
      body: body == null ? undefined : (typeof body === "object" && !(body instanceof Blob) && !(body instanceof ArrayBuffer) ? JSON.stringify(body) : body)
    });
    if (!response.ok) {
      const data = await response.json().catch(function () { return {}; });
      if (response.status === 401) expireOwnerSession();
      throw new Error(data.message || data.error || "Storage request failed (" + response.status + ").");
    }
    if (maxBytes != null) {
      return ULTRON_RUNTIME.readResponseBytes(response, maxBytes);
    }
    return binary ? response.arrayBuffer() : response.json().catch(function () { return null; });
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

  function queryForOwner(ownerId, order, limit) {
    return "select=*&owner_id=eq." + encodeURIComponent(ownerId) + (order ? "&order=" + encodeURIComponent(order) : "") + (limit ? "&limit=" + limit : "");
  }

  function cacheKey() {
    return CACHE_PREFIX + (state.user ? state.user.id : "none");
  }

  function saveSnapshot() {
    if (!hasVerifiedOwnerSession()) return;
    const snapshot = {
      saved_at: new Date().toISOString(),
      status: state.status,
      logs: state.logs,
      switches: state.switches
    };
    try { localStorage.setItem(cacheKey(), JSON.stringify(snapshot)); } catch (_) {}
  }

  function loadSnapshot() {
    if (!hasVerifiedOwnerSession()) return false;
    try {
      const raw = localStorage.getItem(cacheKey());
      if (!raw) return false;
      const snapshot = JSON.parse(raw);
      state.status = snapshot.status || null;
      state.logs = snapshot.logs || [];
      state.switches = snapshot.switches || [];
      state.lastUpdated = snapshot.saved_at || null;
      return true;
    } catch (_) {
      return false;
    }
  }

  async function refreshData() {
    if (!hasVerifiedOwnerSession() || state.refreshing) return;
    const generation = state.authGeneration;
    const ownerId = state.user.id;
    state.refreshing = true;
    try {
      const results = await Promise.all([
        apiRequest("training_status", "GET", queryForOwner(ownerId, "updated_at.desc", 30)),
        apiRequest("server_log", "GET", queryForOwner(ownerId, "started_at.desc", 500)),
        apiRequest("switch_requests", "GET", queryForOwner(ownerId, "requested_at.desc", 200))
      ]);
      if (generation !== state.authGeneration || !hasVerifiedOwnerSession() || state.user.id !== ownerId) return;
      const rows = results[0] || [];
      rows.sort(function (a, b) { return new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0); });
      state.status = rows.find(function (row) { return row.state !== "finished"; }) || rows[0] || null;
      state.logs = results[1] || [];
      state.switches = results[2] || [];
      state.lastUpdated = new Date().toISOString();
      state.stale = false;
      saveSnapshot();
      if (state.status && state.status.run_id) {
        try { await loadCheckpointCandidates(); }
        catch (error) {
          state.checkpoints = [];
          showCheckpointNotice("Checkpoint list could not be loaded: " + error.message, "warn");
        }
      } else {
        state.checkpoints = [];
      }
      setConnection("LIVE", "connected");
      $("lastUpdated").textContent = "Last updated " + formatDateTime(state.lastUpdated);
      renderAll();
    } catch (error) {
      if (generation !== state.authGeneration || !hasVerifiedOwnerSession() || state.user.id !== ownerId) return;
      state.stale = true;
      const hadCache = loadSnapshot();
      setConnection("OUT OF DATE", "stale");
      $("lastUpdated").textContent = hadCache ? "Showing last known status from " + formatDateTime(state.lastUpdated) : "Database is unavailable.";
      showNotice("Cannot reach Supabase right now. " + error.message + (hadCache ? " Showing cached status; it may be out of date." : ""), "warn");
      renderAll();
    } finally {
      state.refreshing = false;
    }
  }

  function formatDateTime(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return date.toLocaleString();
  }

  function formatAge(value) {
    if (!value) return "Unknown";
    const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
    if (!Number.isFinite(seconds)) return "Unknown";
    if (seconds < 60) return seconds + " sec ago";
    if (seconds < 3600) return Math.floor(seconds / 60) + " min ago";
    if (seconds < 86400) return Math.floor(seconds / 3600) + " hr ago";
    return Math.floor(seconds / 86400) + " days ago";
  }

  function formatDuration(seconds) {
    if (seconds == null || !Number.isFinite(Number(seconds))) return "—";
    let value = Math.max(0, Math.floor(Number(seconds)));
    const hours = Math.floor(value / 3600);
    value %= 3600;
    const minutes = Math.floor(value / 60);
    const secs = value % 60;
    if (hours) return hours + "h " + minutes + "m";
    if (minutes) return minutes + "m " + secs + "s";
    return secs + "s";
  }

  function formatNumber(value, digits) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    return number.toLocaleString(undefined, {maximumFractionDigits: digits == null ? 2 : digits});
  }

  function statusAgeSeconds(status) {
    if (!status || !status.last_heartbeat_at) return Infinity;
    return Math.max(0, (Date.now() - new Date(status.last_heartbeat_at).getTime()) / 1000);
  }

  function effectiveState(status) {
    if (!status) return "not started";
    if (status.state === "running" && statusAgeSeconds(status) > STALE_SECONDS) {
      const expiry = status.lease_expires_at ? new Date(status.lease_expires_at).getTime() : 0;
      if (!expiry || expiry <= Date.now()) return "dead";
    }
    if (status.pause_requested && status.state === "running") return "pause requested";
    return String(status.state || "unknown").replace(/_/g, " ");
  }

  function accuracyPercent(value) {
    if (typeof value === "number") return Math.max(0, Math.min(1, value)) * 100;
    if (!value || typeof value !== "object") return null;
    const candidate = value.accuracy != null ? value.accuracy :
      (value.exact_accuracy != null ? value.exact_accuracy :
      (value.correct != null && value.total ? value.correct / value.total : null));
    if (candidate == null) return null;
    const number = Number(candidate);
    if (!Number.isFinite(number)) return null;
    return Math.max(0, Math.min(1, number)) * 100;
  }

  function getQuotaPeriodStart(period) {
    const now = new Date();
    if (period === "weekly") {
      const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
      const day = start.getUTCDay();
      start.setUTCDate(start.getUTCDate() - ((day + 6) % 7));
      return start;
    }
    if (period === "monthly") return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
    return null;
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
    const start = getQuotaPeriodStart(period);
    if (!start) return {used: null, limit: limit, percent: null, label: period === "initial_credits_not_monthly" ? "One-time credits" : "Usage not published"};
    const names = [server.name, server.id];
    let seconds = 0;
    state.logs.forEach(function (log) {
      if (names.indexOf(log.server_name) === -1 && (log.details || {}).server_id !== server.id) return;
      const began = new Date(log.started_at || 0);
      if (Number.isNaN(began.getTime()) || began < start) return;
      let used = Number(log.gpu_seconds || 0);
      if (log.ended_at == null && ((log.details || {}).device === "cuda" || (log.details || {}).compute_device === "cuda")) {
        used = Math.max(used, (Date.now() - began.getTime()) / 1000);
      }
      seconds += Math.max(0, used);
    });
    const used = seconds / 3600;
    return {used: used, limit: limit, percent: limit ? used / limit * 100 : null, label: limit ? formatNumber(used, 1) + " / " + formatNumber(limit, 0) + " GPU hours" : "No fixed public quota"};
  }

  function serverState(server) {
    const statusMap = state.status && state.status.server_statuses ? state.status.server_statuses : {};
    const saved = statusMap[server.id] || {};
    const current = state.status && state.status.current_server === server.name && effectiveState(state.status) === "running";
    if (current) return "running";
    const savedStatus = saved.status || server.current_status || "unknown";
    if (savedStatus === "unavailable_until" && saved.unavailable_until && new Date(saved.unavailable_until).getTime() <= Date.now()) return "unknown";
    if (savedStatus === "kicked_out" && saved.kicked_out_until && new Date(saved.kicked_out_until).getTime() <= Date.now()) return "unknown";
    const quota = quotaUsage(server);
    if (quota.percent != null && quota.percent >= 95) return "out_of_quota";
    return savedStatus;
  }

  function chooseNextServer() {
    const currentName = state.status ? state.status.current_server : null;
    for (const server of state.servers) {
      if (server.enabled === false || server.id === (state.status && state.status.current_server_id)) continue;
      if (server.name === currentName) continue;
      const status = serverState(server);
      const quota = quotaUsage(server);
      if (status !== "ready") continue;
      if (quota.percent != null && quota.percent >= 90) continue;
      return {server: server, fallback: false};
    }
    const fallbackId = "github_actions_cpu";
    const fallback = state.servers.find(function (server) { return server.id === fallbackId && server.enabled !== false; });
    if (fallback && serverState(fallback) !== "out_of_quota" && serverState(fallback) !== "unavailable_until") {
      return {server: fallback, fallback: true};
    }
    return null;
  }

  function renderNextAction() {
    const status = state.status;
    const title = $("nextActionTitle");
    const text = $("nextActionText");
    const meta = $("nextActionMeta");
    const link = $("nextServerButton");
    link.hidden = true;
    if (state.publicMode) {
      title.textContent = "Welcome to the ULTRON guest dashboard";
      text.textContent = "You can browse public system information without an account. Private training status, history and checkpoints are not loaded in Guest Mode.";
      meta.textContent = "Guest access · no private data or training commands";
      return;
    }
    if (!status) {
      title.textContent = "No training run found";
      text.textContent = "Open the ULTRON training notebook and press Run All. It will create a run and request the single-writer lease.";
      meta.textContent = "The dashboard will show the run after its first status update.";
      return;
    }
    const derived = effectiveState(status);
    if (derived === "finished") {
      title.textContent = "Training finished";
      text.textContent = "The current run is complete. Review its evaluation results before preparing a model release.";
      meta.textContent = "No server switch is required.";
      return;
    }
    const age = statusAgeSeconds(status);
    if (derived === "running" && age <= STALE_SECONDS && !status.handoff_requested) {
      title.textContent = "Running on " + (status.current_server || "a server");
      text.textContent = "Training is healthy. Nothing to do right now.";
      meta.textContent = "Heartbeat " + formatAge(status.last_heartbeat_at) + " · Checkpoint " + formatAge(status.last_checkpoint_at);
      return;
    }
    if (status.pause_requested && status.lease_holder && status.lease_expires_at && new Date(status.lease_expires_at).getTime() > Date.now() && derived !== "dead") {
      title.textContent = "Pause requested";
      text.textContent = "The active notebook will save a checkpoint and release its lease at the next heartbeat. Wait for the state to change before starting another server.";
      meta.textContent = "Only one server can train at a time.";
      return;
    }
    const next = chooseNextServer();
    if (!next) {
      title.textContent = "No server is currently ready";
      text.textContent = "Check your provider accounts and mark one free server as Ready after confirming its quota and hardware.";
      meta.textContent = "The dashboard will not assume a provider is available.";
      return;
    }
    const server = next.server;
    title.textContent = derived === "dead" ? "The previous run appears dead" : "Handoff needed";
    if (server.id === "github_actions_cpu") {
      text.textContent = status.automatic_start_enabled ? "CPU fallback is only a provider option; training must be started inside the provider session." : "Open GitHub Actions, select ULTRON CPU Training, and press Run workflow.";
    } else if (server.id === "kaggle") {
      text.textContent = status.automatic_start_enabled ? "Open the provider notebook and make any training decision inside that session." : "Open Kaggle, choose the free GPU if available, and press Run All.";
    } else if (server.id === "google_colab") {
      text.textContent = "Open Colab, select a free GPU if offered, then press Runtime → Run all.";
    } else if (server.id === "lightning_ai") {
      text.textContent = "Open Lightning AI, confirm the Studio is free, then open train.py and run it.";
    } else {
      text.textContent = "Open the selected free server and run the ULTRON training entry point.";
    }
    meta.textContent = "Next in rotation: " + server.name + (next.fallback ? " · CPU fallback" : "") + " · Last heartbeat " + formatAge(status.last_heartbeat_at);
    link.href = server.notebook_open_url || server.notebook_url || server.documentation_url || "#";
    link.textContent = "Open " + server.name + " ↗";
    link.hidden = false;
  }

  function renderMetrics() {
    const status = state.status;
    $("metricState").textContent = status ? effectiveState(status).toUpperCase() : "NOT STARTED";
    $("metricStateDetail").textContent = status ? (status.current_server || "No server assigned") : "No active run";
    $("metricStep").textContent = status ? formatNumber(status.current_step || 0, 0) : "0";
    $("metricTopic").textContent = status ? (status.current_topic || "Topic not reported") : "Topic not started";
    $("metricLoss").textContent = status && status.loss != null ? formatNumber(status.loss, 5) : "—";
    let left = status ? status.session_time_left_seconds : null;
    if (status && left == null && status.session_started_at && status.session_limit_seconds) {
      left = Math.max(0, Number(status.session_limit_seconds) - (Date.now() - new Date(status.session_started_at).getTime()) / 1000);
    }
    $("metricTimeLeft").textContent = left == null ? "—" : formatDuration(left);
    $("metricSessionAge").textContent = status && status.session_started_at ? "Session started " + formatAge(status.session_started_at) : "Session not running";
    $("heartbeatAge").textContent = status ? formatAge(status.last_heartbeat_at) : "—";
    $("checkpointAge").textContent = status ? formatAge(status.last_checkpoint_at) : "—";
    $("activeServer").textContent = status ? (status.current_server || "—") : "—";
    const expiry = status && status.lease_expires_at ? new Date(status.lease_expires_at).getTime() : 0;
    $("leaseState").textContent = status && status.lease_holder && expiry > Date.now() ? "HELD" : "RELEASED";
  }

  function renderMastery() {
    const container = $("masteryList");
    const data = state.status && state.status.accuracy_by_topic ? state.status.accuracy_by_topic : {};
    const entries = Object.entries(data);
    $("masteryCount").textContent = entries.length + " topics";
    if (!entries.length) {
      container.innerHTML = '<p class="empty-state">Topic accuracy will appear here after evaluation.</p>';
      return;
    }
    container.innerHTML = entries.map(function (entry) {
      const value = accuracyPercent(entry[1]);
      const percent = value == null ? 0 : value;
      return '<div class="mastery-row"><div class="mastery-label"><span>' + escapeHtml(entry[0].replace(/_/g, " ")) + '</span><strong>' + (value == null ? "—" : formatNumber(value, 1) + "%") + '</strong></div><div class="progress-track"><div class="progress-fill" style="width:' + percent + '%"></div></div></div>';
    }).join("");
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
    const points = state.status && Array.isArray(state.status.loss_history) ? state.status.loss_history.filter(function (point) {
      return Number.isFinite(Number(point.loss));
    }) : [];
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
    const nextChoice = chooseNextServer();
    const nextId = nextChoice && nextChoice.server ? nextChoice.server.id : null;
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
      const localRamValue = $("deviceRamLimitValue");
      if (localRamValue) localRamValue.textContent = state.ramLimitGb + " GB";
      $("ramLimitStatus").textContent = "Saved on this browser only. It does not enforce a memory cap or control a training process.";
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

  function renderCheckpointList() {
    const container = $("checkpointList");
    if (state.publicMode) {
      container.innerHTML = '<div class="empty-state panel">Checkpoint access is locked on the public dashboard. No personal checkpoint history is loaded or displayed.</div>';
      return;
    }
    if (!state.status || !state.status.run_id) {
      container.innerHTML = '<div class="empty-state panel">Start a training run before managing checkpoints.</div>';
      return;
    }
    if (!state.checkpoints.length) {
      container.innerHTML = '<div class="empty-state panel">No remote checkpoint manifests found for this run yet.</div>';
      return;
    }
    container.innerHTML = state.checkpoints.map(function (item) {
      const verified = item.full_verified ? "FULLY VERIFIED" : "MANIFEST FOUND";
      return '<article class="checkpoint-card">' +
        '<div><div class="checkpoint-title">' + escapeHtml(item.checkpoint_id) + '</div>' +
        '<div class="checkpoint-details"><span class="meta-chip">Step ' + escapeHtml(formatNumber(item.step, 0)) + '</span><span class="meta-chip">' + escapeHtml(formatNumber(Number(item.total_size_bytes || 0) / 1048576, 1)) + ' MB</span><span class="meta-chip">' + escapeHtml(verified) + '</span><span class="meta-chip">' + escapeHtml(item.created_at || "Time not recorded") + '</span></div></div>' +
        '<div class="checkpoint-actions"><button class="secondary-button" type="button" data-checkpoint-verify="' + escapeHtml(item.checkpoint_id) + '">Verify</button><button class="secondary-button" type="button" data-checkpoint-download="' + escapeHtml(item.checkpoint_id) + '">Download</button></div>' +
      '</article>';
    }).join("");
  }

  function renderActivity() {
    const logs = $("activityLogs");
    const switches = $("activitySwitches");
    if (state.publicMode || !hasVerifiedOwnerSession()) {
      logs.innerHTML = '<p class="empty-state">Training activity is private. Sign in to the verified ULTRON owner account to view it.</p>';
      switches.innerHTML = '<p class="empty-state">Server handoff records are private to the ULTRON owner.</p>';
      return;
    }
    if (!state.logs.length) {
      logs.innerHTML = '<p class="empty-state">No training sessions have been recorded yet.</p>';
    } else {
      logs.innerHTML = '<div class="table-scroll"><table><thead><tr><th>Server</th><th>Started</th><th>Duration</th><th>Result</th></tr></thead><tbody>' +
        state.logs.slice(0, 500).map(function (item) {
          return '<tr><td>' + escapeHtml(item.server_name || "Unknown") + '</td><td>' + escapeHtml(formatDateTime(item.started_at)) + '</td><td>' + escapeHtml(formatDuration(item.gpu_seconds)) + '</td><td>' + escapeHtml(item.end_reason || (item.ended_at ? "Completed" : "In progress")) + '</td></tr>';
        }).join("") + '</tbody></table></div>';
    }
    if (!state.switches.length) {
      switches.innerHTML = '<p class="empty-state">No server handoffs have been recorded yet.</p>';
    } else {
      switches.innerHTML = '<div class="table-scroll"><table><thead><tr><th>Requested</th><th>From</th><th>To</th><th>Reason</th><th>Result</th></tr></thead><tbody>' +
        state.switches.slice(0, 200).map(function (item) {
          return '<tr><td>' + escapeHtml(formatDateTime(item.requested_at)) + '</td><td>' + escapeHtml(item.from_server || "—") + '</td><td>' + escapeHtml(item.to_server || "—") + '</td><td>' + escapeHtml(item.reason || "—") + '</td><td>' + escapeHtml(item.result || "Pending") + '</td></tr>';
        }).join("") + '</tbody></table></div>';
    }
  }

  function renderAll() {
    renderNextAction();
    renderMetrics();
    renderActivity();
    renderMastery();
    scheduleChartDraw();
    renderServers();
    renderSettings();
    renderCheckpointList();
    renderDataLibrary();
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
      activity: ["ACTIVITY", "Training activity"],
      servers: ["SERVERS", "Free compute servers"],
      checkpoints: ["CHECKPOINTS", "Verified checkpoints"],
      data: ["DATA LIBRARY", "Owner data library"],
      ask: ["ASK ULTRON", "Ask questions about your data"],
      settings: ["SETTINGS", "System settings"],
      devices: ["LOCAL TRAINING", "Local training"]
    };
    $("viewName").textContent = labels[view][0];
    $("pageTitle").textContent = labels[view][1];
    if (view === "overview") scheduleChartDraw();
    if (view === "data") loadDataLibrary().catch(function (error) { showDataLibraryNotice(error.message, "error"); });
    if (view === "checkpoints") loadCheckpointCandidates().then(renderCheckpointList).catch(function (error) {
      showCheckpointNotice(error.message, "warn");
    });
  }

  function objectPath(parts) {
    return parts.map(function (part) { return encodeURIComponent(String(part)); }).join("/");
  }

  async function getStorageBytes(path, maxBytes) {
    return storageRequest("object/authenticated/checkpoints/" + objectPath(path.split("/")), "GET", null, true,
      maxBytes == null ? ULTRON_RUNTIME.MAX_FILE_BYTES : maxBytes);
  }

  async function getStorageJson(path) {
    const bytes = await getStorageBytes(path, ULTRON_RUNTIME.MAX_METADATA_BYTES);
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  async function sha256Hex(bytes) {
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest)).map(function (value) { return value.toString(16).padStart(2, "0"); }).join("");
  }


  async function loadCheckpointCandidates() {
    if (!hasVerifiedOwnerSession() || !state.status || !state.status.run_id) {
      state.checkpoints = [];
      return [];
    }
    const generation = state.authGeneration;
    const ownerId = state.user.id;
    const runId = state.status.run_id;
    const prefix = ownerId + "/" + runId;
    const maximumCommittedStep = state.status.last_checkpoint_step == null ? -1 : Number(state.status.last_checkpoint_step);
    const listed = await storageRequest("object/list/checkpoints", "POST", {
      prefix: prefix,
      limit: 1000,
      offset: 0,
      sortBy: {column: "name", order: "asc"}
    }, false);
    if (generation !== state.authGeneration || !hasVerifiedOwnerSession() ||
        state.user.id !== ownerId || !state.status || state.status.run_id !== runId) {
      return [];
    }
    const ids = Array.from(new Set((listed || []).map(function (item) {
      return String(item.name || "").split("/")[0];
    }).filter(function (id) { return id.indexOf("ckpt-") === 0; })));
    const results = await ULTRON_RUNTIME.mapWithConcurrency(ids, 3, async function (id) {
      try {
        const base = prefix + "/" + id;
        const metadata = await Promise.all([
          getStorageBytes(base + "/manifest.json", ULTRON_RUNTIME.MAX_METADATA_BYTES),
          getStorageJson(base + "/upload_receipt.json")
        ]);
        const manifestBytes = metadata[0];
        const receipt = metadata[1];
        const manifestHash = await sha256Hex(manifestBytes);
        const manifest = JSON.parse(new TextDecoder().decode(manifestBytes));
        const manifestStats = ULTRON_RUNTIME.validateManifest(manifest, id);
        if (manifestStats.totalBytes + manifestBytes.byteLength + ULTRON_RUNTIME.MAX_METADATA_BYTES > ULTRON_RUNTIME.MAX_TOTAL_BYTES) return null;
        if (manifest.checkpoint_id !== id || receipt.checkpoint_id !== id || receipt.manifest_sha256 !== manifestHash) return null;
        if (JSON.stringify(receipt.files) !== JSON.stringify(manifest.files)) return null;
        const total = manifestStats.totalBytes + manifestBytes.byteLength;
        if (Number(manifest.step) > maximumCommittedStep) return null;
        return Object.assign({}, manifest, {
          checkpoint_id: id,
          manifest_sha256: manifestHash,
          total_size_bytes: total,
          full_verified: false,
          created_at: manifest.created_at || manifest.timestamp || null
        });
      } catch (_) {
        return null;
      }
    });
    if (generation !== state.authGeneration || !hasVerifiedOwnerSession() ||
        state.user.id !== ownerId || !state.status || state.status.run_id !== runId) {
      return [];
    }
    const candidates = results.filter(Boolean);
    candidates.sort(function (a, b) { return Number(b.step || 0) - Number(a.step || 0); });
    state.checkpoints = candidates;
    return candidates;
  }

  async function verifyCheckpoint(candidate) {
    const prefix = state.user.id + "/" + state.status.run_id + "/" + candidate.checkpoint_id;
    const manifestBytes = await getStorageBytes(prefix + "/manifest.json", ULTRON_RUNTIME.MAX_METADATA_BYTES);
    const receiptBytes = await getStorageBytes(prefix + "/upload_receipt.json", ULTRON_RUNTIME.MAX_METADATA_BYTES);
    const manifestHash = await sha256Hex(manifestBytes);
    const manifest = JSON.parse(new TextDecoder().decode(manifestBytes));
    const receipt = JSON.parse(new TextDecoder().decode(receiptBytes));
    const manifestStats = ULTRON_RUNTIME.validateManifest(manifest, candidate.checkpoint_id);
    if (manifest.checkpoint_id !== candidate.checkpoint_id || receipt.checkpoint_id !== candidate.checkpoint_id) throw new Error("Checkpoint identity does not match.");
    if (receipt.manifest_sha256 !== manifestHash) throw new Error("Manifest checksum does not match the upload receipt.");
    if (JSON.stringify(receipt.files) !== JSON.stringify(manifest.files)) throw new Error("Receipt file list does not match the manifest.");
    let stateFile = null;
    let verifiedBytes = manifestBytes.byteLength + receiptBytes.byteLength;
    if (verifiedBytes + manifestStats.totalBytes > ULTRON_RUNTIME.MAX_TOTAL_BYTES) throw new Error("Checkpoint exceeds the 256 MiB total size limit.");
    for (const entry of Object.entries(manifest.files || {})) {
      const name = entry[0];
      const metadata = entry[1];
      const bytes = await getStorageBytes(prefix + "/" + name, ULTRON_RUNTIME.MAX_FILE_BYTES);
      verifiedBytes += bytes.byteLength;
      if (verifiedBytes > ULTRON_RUNTIME.MAX_TOTAL_BYTES) throw new Error("Checkpoint exceeds the 256 MiB total size limit.");
      if (bytes.byteLength !== Number(metadata.size_bytes)) throw new Error("File size mismatch: " + name);
      if (await sha256Hex(bytes) !== metadata.sha256) throw new Error("SHA-256 mismatch: " + name);
      if (name === "state.json") stateFile = JSON.parse(new TextDecoder().decode(bytes));
    }
    if (!stateFile || stateFile.checkpoint_id !== candidate.checkpoint_id) throw new Error("Checkpoint state metadata is missing or inconsistent.");
    if (!stateFile.state || Number(stateFile.state.step) !== Number(manifest.step)) throw new Error("Checkpoint step metadata is inconsistent.");
    candidate.full_verified = true;
    candidate.manifest_sha256 = manifestHash;
    candidate.total_size_bytes = manifestStats.totalBytes + manifestBytes.byteLength + receiptBytes.byteLength;
    candidate.state = stateFile.state;
    return candidate;
  }

  async function verifyOneCheckpoint(id) {
    const candidate = state.checkpoints.find(function (item) { return item.checkpoint_id === id; });
    if (!candidate) throw new Error("Checkpoint not found in the current list.");
    showCheckpointNotice("Verifying every file in " + id + "…", "");
    await verifyCheckpoint(candidate);
    renderCheckpointList();
    showCheckpointNotice("Checkpoint " + id + " passed its full SHA-256 verification.", "success");
  }

  function triggerDownload(name, bytes) {
    const blob = new Blob([bytes], {type: name.endsWith(".json") ? "application/json" : "application/octet-stream"});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 30000);
  }

  async function downloadCheckpoint(id) {
    const prefix = state.user.id + "/" + state.status.run_id + "/" + id;
    const manifest = await getStorageJson(prefix + "/manifest.json");
    const stats = ULTRON_RUNTIME.validateManifest(manifest, id);
    if (stats.totalBytes + ULTRON_RUNTIME.MAX_METADATA_BYTES * 2 > ULTRON_RUNTIME.MAX_TOTAL_BYTES) throw new Error("Checkpoint exceeds the 256 MiB total size limit.");
    const names = Object.keys(manifest.files || {}).concat(["manifest.json", "upload_receipt.json"]);
    for (const name of names) {
      const bytes = await getStorageBytes(prefix + "/" + name, name === "manifest.json" || name === "upload_receipt.json" ? ULTRON_RUNTIME.MAX_METADATA_BYTES : ULTRON_RUNTIME.MAX_FILE_BYTES);
      triggerDownload(id + "-" + name, bytes);
    }
    showCheckpointNotice("Checkpoint files downloaded separately. Keep every component in the same checkpoint folder.", "success");
  }

  async function handleCheckpointAction(button) {
    const id = button.getAttribute("data-checkpoint-verify") || button.getAttribute("data-checkpoint-download");
    if (button.hasAttribute("data-checkpoint-verify")) return verifyOneCheckpoint(id);
    if (button.hasAttribute("data-checkpoint-download")) return downloadCheckpoint(id);
  }

  const DATA_LIBRARY_BUCKET = "data-library";
  const DATA_LIBRARY_MAX_BYTES = 20 * 1024 * 1024;

  function showDataLibraryNotice(message, kind) {
    const box = $("dataLibraryNotice");
    if (!box) return;
    box.textContent = message;
    box.className = "notice" + (kind ? " notice-" + kind : "");
    box.hidden = !message;
  }

  function safeDataFileName(value) {
    const name = String(value || "").trim();
    if (!/^[A-Za-z0-9][A-Za-z0-9._ -]{0,179}$/.test(name) || name === "." || name === ".." || name.startsWith(".")) {
      throw new Error("Use a simple file name (1–180 characters), without folders or hidden-file names.");
    }
    return name;
  }

  async function dataLibraryRequest(path, method, body, fileBlob, binary) {
    const session = await ensureSession();
    assertOwnerAccess(session);
    const headers = {"apikey": PUBLISHABLE_KEY, "Authorization": "Bearer " + session.access_token};
    if (body != null && !fileBlob) headers["Content-Type"] = "application/json";
    if (fileBlob) {
      headers["Content-Type"] = "application/octet-stream";
      headers["x-upsert"] = "true";
    }
    const response = await fetch(STORAGE_ROOT + path, {
      method: method,
      headers: headers,
      body: body == null ? undefined : (fileBlob ? fileBlob : JSON.stringify(body)),
      cache: "no-store"
    });
    if (!response.ok) {
      const rawError = await response.text();
      const errorData = rawError ? (function () { try { return JSON.parse(rawError); } catch (_) { return rawError; } })() : null;
      if (response.status === 401) expireOwnerSession();
      throw new Error(errorData && (errorData.message || errorData.error) || "Private data library request failed (" + response.status + ").");
    }
    if (binary) return response.arrayBuffer();
    const raw = await response.text();
    const data = raw ? (function () { try { return JSON.parse(raw); } catch (_) { return raw; } })() : null;
    return data;
  }

  function renderDataLibrary() {
    const container = $("dataFileList");
    if (!container) return;
    if (!hasVerifiedOwnerSession()) {
      state.dataFiles = [];
      container.innerHTML = '<p class="empty-state">Private library locked. Sign in to the verified owner account.</p>';
      $("dataSyncStatus").textContent = "No private files are loaded in Guest Mode.";
      return;
    }
    if (!state.dataFiles.length) {
      container.innerHTML = '<p class="empty-state">No files uploaded yet. Choose a file above to add the first item.</p>';
      return;
    }
    container.innerHTML = state.dataFiles.map(function (file) {
      const name = safeDataFileName(file.name);
      const size = Number(file.metadata && file.metadata.size || file.size || 0);
      const updated = file.updated_at || file.created_at || "";
      return '<article class="data-file-card"><div class="data-file-main"><strong>' + escapeHtml(name) + '</strong><small>' + escapeHtml(formatNumber(size / 1048576, 2)) + ' MB · ' + escapeHtml(formatDateTime(updated)) + '</small></div><div class="data-file-actions"><button class="secondary-button" type="button" data-data-download="' + escapeHtml(name) + '">Download</button><button class="quiet-button" type="button" data-data-delete="' + escapeHtml(name) + '">Delete</button></div></article>';
    }).join("");
  }

  async function loadDataLibrary() {
    if (!hasVerifiedOwnerSession()) {
      state.dataFiles = [];
      renderDataLibrary();
      return [];
    }
    const generation = state.authGeneration;
    const ownerId = state.user.id;
    const listed = await dataLibraryRequest("object/list/" + DATA_LIBRARY_BUCKET, "POST", {
      prefix: ownerId, limit: 500, offset: 0, sortBy: {column: "name", order: "asc"}
    }, false);
    if (generation !== state.authGeneration || !hasVerifiedOwnerSession() || state.user.id !== ownerId) return [];
    state.dataFiles = (Array.isArray(listed) ? listed : []).filter(function (item) {
      return item && typeof item.name === "string" && item.name && item.name.indexOf("/") === -1 && item.name !== "." && item.name !== "..";
    }).sort(function (a, b) { return a.name.localeCompare(b.name); });
    $("dataSyncStatus").textContent = "Cloud library · " + state.dataFiles.length + " file(s) · last synced " + new Date().toLocaleTimeString();
    renderDataLibrary();
    return state.dataFiles;
  }


  const ASK_TEXT_EXTENSIONS = [".txt", ".md", ".csv", ".json", ".lean", ".toml", ".yaml", ".yml", ".py", ".js", ".ts", ".html", ".xml", ".log"];
  const ASK_MAX_TOTAL_BYTES = 15 * 1024 * 1024;
  const ASK_MAX_FILE_BYTES = 5 * 1024 * 1024;

  function splitAskPassages(text, fileName) {
    const clean = String(text || "").replace(/\r/g, "").replace(/[\t ]+/g, " ").trim();
    if (!clean) return [];
    const passages = [];
    const size = 1100;
    const overlap = 140;
    for (let start = 0; start < clean.length; start += size - overlap) {
      const content = clean.slice(start, start + size).trim();
      if (content.length >= 35) passages.push({fileName: fileName, text: content});
      if (start + size >= clean.length) break;
    }
    return passages;
  }

  async function readDataLibraryForQuestions() {
    if (!hasVerifiedOwnerSession()) throw new Error("Sign in to the verified owner account to ask questions about private data.");
    const files = await loadDataLibrary();
    const passages = [];
    let totalBytes = 0;
    let skipped = 0;
    for (const file of files) {
      const name = safeDataFileName(file.name);
      const lower = name.toLowerCase();
      if (!ASK_TEXT_EXTENSIONS.some(function (extension) { return lower.endsWith(extension); })) {
        skipped += 1;
        continue;
      }
      const size = Number(file.metadata && file.metadata.size || file.size || 0);
      if (!Number.isFinite(size) || size < 1 || size > ASK_MAX_FILE_BYTES || totalBytes + size > ASK_MAX_TOTAL_BYTES) {
        skipped += 1;
        continue;
      }
      try {
        const bytes = await dataLibraryRequest("object/authenticated/" + DATA_LIBRARY_BUCKET + "/" + objectPath([state.user.id, name]), "GET", null, false, true);
        const text = new TextDecoder("utf-8", {fatal: true}).decode(bytes);
        totalBytes += bytes.byteLength;
        passages.push.apply(passages, splitAskPassages(text, name));
      } catch (_) {
        skipped += 1;
      }
    }
    return {passages: passages, skipped: skipped, totalBytes: totalBytes};
  }

  function rankAskPassages(question, passages) {
    const stopWords = new Set(["the","and","for","that","with","this","from","what","when","where","which","who","why","how","does","did","are","was","were","can","could","would","should","about","into","have","has","had","you","your","its","their","them","then","than","not","but","all","any","use","using"]);
    const terms = String(question || "").toLowerCase().match(/[a-z0-9_]{2,}/g) || [];
    const uniqueTerms = Array.from(new Set(terms.filter(function (term) { return !stopWords.has(term); })));
    if (!uniqueTerms.length) return [];
    return passages.map(function (passage) {
      const content = passage.text.toLowerCase();
      const words = content.match(/[a-z0-9_]{2,}/g) || [];
      const frequencies = new Map();
      words.forEach(function (word) { frequencies.set(word, (frequencies.get(word) || 0) + 1); });
      let score = 0;
      let matched = 0;
      uniqueTerms.forEach(function (term) {
        const count = frequencies.get(term) || 0;
        if (count > 0) {
          matched += 1;
          score += Math.min(count, 5) * 2;
        }
      });
      const phrase = String(question || "").trim().toLowerCase();
      if (phrase.length > 5 && content.includes(phrase)) score += 8;
      if (matched > 1) score += matched;
      return {fileName: passage.fileName, text: passage.text, score: score, matched: matched};
    }).filter(function (item) { return item.score > 0; })
      .sort(function (a, b) { return b.score - a.score; }).slice(0, 5);
  }

  async function askUltron(question) {
    if (!hasVerifiedOwnerSession()) throw new Error("Owner sign-in is required.");
    const query = String(question || "").trim();
    if (query.length < 3) throw new Error("Enter a question with at least 3 characters.");
    if (query.length > 500) throw new Error("Keep the question under 500 characters.");
    if (state.askBusy) return;
    state.askBusy = true;
    const button = $("askSubmitButton");
    const output = $("askResults");
    button.disabled = true;
    output.textContent = "Reading your private text files and searching for evidence…";
    try {
      const library = await readDataLibraryForQuestions();
      if (!library.passages.length) {
        output.textContent = "I couldn't find any readable text files. Supported formats: TXT, Markdown, CSV, JSON, Lean, TOML, YAML, Python, JavaScript, TypeScript, HTML, XML and LOG. PDF and other binary formats aren't supported yet.";
        return;
      }
      const matches = rankAskPassages(query, library.passages);
      if (!matches.length) {
        output.textContent = "I couldn't find evidence for that question in the readable files. Try different words or add a relevant file to the Data Library.";
        return;
      }
      const intro = document.createElement("p");
      intro.className = "ask-answer-intro";
      intro.textContent = "I found these relevant passages in your data. The results below are quoted evidence, not a generated answer.";
      const list = document.createElement("div");
      list.className = "ask-evidence-list";
      matches.forEach(function (match) {
        const card = document.createElement("article");
        card.className = "ask-evidence-card";
        const source = document.createElement("strong");
        source.textContent = match.fileName;
        const excerpt = document.createElement("p");
        excerpt.textContent = match.text;
        card.appendChild(source);
        card.appendChild(excerpt);
        list.appendChild(card);
      });
      output.replaceChildren(intro, list);
      $("askStatus").textContent = "Searched " + library.passages.length + " passages from " + new Set(library.passages.map(function (item) { return item.fileName; })).size + " file(s)." + (library.skipped ? " Skipped " + library.skipped + " unsupported, unreadable or oversized file(s)." : "");
    } finally {
      state.askBusy = false;
      button.disabled = false;
    }
  }

  async function uploadDataFile() {
    if (!hasVerifiedOwnerSession()) throw new Error("Sign in to the verified owner account before uploading.");
    const input = $("dataFileInput");
    const file = input.files && input.files[0];
    if (!file) throw new Error("Choose a file first.");
    if (file.size < 1 || file.size > DATA_LIBRARY_MAX_BYTES) throw new Error("Files must be between 1 byte and 20 MiB.");
    const name = safeDataFileName(file.name);
    const button = $("dataUploadButton");
    if (state.dataLibraryBusy) return;
    state.dataLibraryBusy = true;
    button.disabled = true;
    try {
      await dataLibraryRequest("object/" + DATA_LIBRARY_BUCKET + "/" + objectPath([state.user.id, name]), "POST", file, true);
      input.value = "";
      showDataLibraryNotice("Uploaded " + name + ". Other signed-in browsers will see it on their next sync.", "success");
      await loadDataLibrary();
    } finally {
      state.dataLibraryBusy = false;
      button.disabled = false;
    }
  }

  async function downloadDataFile(name) {
    if (!hasVerifiedOwnerSession()) throw new Error("Owner sign-in is required.");
    const safeName = safeDataFileName(name);
    const bytes = await dataLibraryRequest("object/authenticated/" + DATA_LIBRARY_BUCKET + "/" + objectPath([state.user.id, safeName]), "GET", null, false, true);
    const blob = new Blob([bytes], {type: "application/octet-stream"});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = safeName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 30000);
  }

  async function deleteDataFile(name) {
    if (!hasVerifiedOwnerSession()) throw new Error("Owner sign-in is required.");
    const safeName = safeDataFileName(name);
    if (!window.confirm("Delete " + safeName + " from the shared ULTRON data library? This affects every browser.")) return;
    await dataLibraryRequest("object/" + DATA_LIBRARY_BUCKET, "DELETE", {prefixes: [state.user.id + "/" + safeName]}, false);
    showDataLibraryNotice("Deleted " + safeName + " from the cloud library.", "success");
    await loadDataLibrary();
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

  function copyOwnerId() {
    if (!state.user) return;
    const value = state.user.id;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(function () { showNotice("Account UUID copied.", "success"); }).catch(function () { window.prompt("Copy your account UUID", value); });
    } else {
      window.prompt("Copy your account UUID", value);
    }
  }

  function bindEvents() {
    $("themeToggle").addEventListener("click", function () {
      applyTheme(document.body.getAttribute("data-theme") === "dark" ? "light" : "dark");
      scheduleChartDraw();
    });
    $("refreshButton").addEventListener("click", refreshData);
    $("ownerSignInButton").addEventListener("click", function () {
      showAuthMessage("", "");
      if (typeof $("ownerSignInDialog").showModal === "function") $("ownerSignInDialog").showModal();
      else showAuthMessage("This browser does not support the sign-in dialog. Update the browser or continue in Guest Mode.", "warn");
    });
    $("ownerSignOutButton").addEventListener("click", function () { signOutOwner().catch(function (error) { showNotice(error.message, "error"); }); });
    $("ownerSignInForm").addEventListener("submit", signInOwner);
    $("ownerCancelButton").addEventListener("click", function () { $("ownerSignInDialog").close(); });
    document.querySelectorAll("[data-view]").forEach(function (button) {
      button.addEventListener("click", function () { switchView(button.getAttribute("data-view")); });
    });
    $("ramLimitSlider").addEventListener("input", function () {
      const selected = Math.max(2, Math.min(10, Number($("ramLimitSlider").value)));
      state.ramLimitGb = Math.round(selected * 2) / 2;
      $("ramLimitValue").textContent = state.ramLimitGb + " GB";
      const localRamValue = $("deviceRamLimitValue");
      if (localRamValue) localRamValue.textContent = state.ramLimitGb + " GB";
      try { localStorage.setItem(RAM_LIMIT_KEY, String(state.ramLimitGb)); } catch (_) {}
      $("ramLimitStatus").textContent = "Saved as " + state.ramLimitGb + " GB on this browser only. This is a preference only; it does not enforce a memory cap.";
    });


    $("dataUploadForm").addEventListener("submit", function (event) {
      event.preventDefault();
      uploadDataFile().catch(function (error) { showDataLibraryNotice(error.message, "error"); });
    });
    $("dataRefreshButton").addEventListener("click", function () {
      loadDataLibrary().catch(function (error) { showDataLibraryNotice(error.message, "error"); });
    });
    $("askQuestionForm").addEventListener("submit", function (event) {
      event.preventDefault();
      askUltron($("askQuestionInput").value).catch(function (error) { $("askResults").textContent = error.message; });
    });
    $("dataFileList").addEventListener("click", function (event) {
      const button = event.target.closest("[data-data-download], [data-data-delete]");
      if (!button) return;
      const name = button.getAttribute("data-data-download") || button.getAttribute("data-data-delete");
      const action = button.hasAttribute("data-data-download") ? downloadDataFile : deleteDataFile;
      action(name).catch(function (error) { showDataLibraryNotice(error.message, "error"); });
    });
    $("checkpointList").addEventListener("click", function (event) {
      const button = event.target.closest("[data-checkpoint-verify], [data-checkpoint-download]");
      if (button) handleCheckpointAction(button).catch(function (error) { showCheckpointNotice(error.message, "error"); });
    });
    window.addEventListener("resize", scheduleChartDraw);
    if (typeof ResizeObserver === "function") {
      const chart = $("lossChart");
      if (chart && chart.parentElement) {
        const observer = new ResizeObserver(scheduleChartDraw);
        observer.observe(chart.parentElement);
      }
    }
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden && state.user) {
        refreshData();
        if (hasVerifiedOwnerSession()) loadDataLibrary().catch(function () {});
      }
    });
    window.setInterval(function () {
      if (!document.hidden && hasVerifiedOwnerSession()) {
        refreshData();
        loadDataLibrary().catch(function () {});
      }
    }, 20000);
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
    state.session = loadSavedSession();
    state.user = state.session && state.session.user ? state.session.user : null;
    const restoredOwner = await verifyOwnerSession();
    setAccessMode(restoredOwner);
    if (restoredOwner) {
      $("lastUpdated").textContent = "Restored verified owner session.";
      await refreshData();
    } else {
      $("lastUpdated").textContent = "Public system information · no personal training history";
      showNotice("Guest Mode is active. Public information is available without an account. Private training status, history, checkpoints and device controls are not loaded in Guest Mode. Training remains disabled until local device controls and resource safeguards are validated.", "info");
    }
    renderAll();
  }

  document.addEventListener("DOMContentLoaded", init);
})();