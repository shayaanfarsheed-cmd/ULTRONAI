(function () {
  "use strict";
  const config = window.ULTRON_CONFIG || {};
  const endpoint = String(config.trainingControlFunctionUrl ||
    String(config.supabaseUrl || "").replace(/\/$/, "") + "/functions/v1/training-control");
  const $ = (id) => document.getElementById(id);
  let busy = false;
  let pollTimer = null;

  function ownerSession() {
    try {
      const session = JSON.parse(sessionStorage.getItem("ultron_training_session") || "null");
      return session && session.access_token && session.user &&
        config.ownerUserId && session.user.id === config.ownerUserId ? session : null;
    } catch (_) { return null; }
  }

  function message(text, kind) {
    const node = $("trainingControlMessage");
    if (!node) return;
    node.textContent = text;
    node.className = "notice" + (kind ? " notice-" + kind : "");
    node.hidden = !text;
  }

  function setStatus(run) {
    const label = $("trainingControlState");
    const details = $("trainingControlDetails");
    const stop = $("trainingStopButton");
    const link = $("trainingRunLink");
    if (!run) {
      label.textContent = "NO RECENT WORKFLOW";
      details.textContent = "No GitHub Actions run was found.";
      stop.disabled = true;
      link.hidden = true;
      return;
    }
    label.textContent = String(run.status || "unknown").replace(/_/g, " ").toUpperCase();
    details.textContent = [run.conclusion || "No conclusion yet", run.created_at ? new Date(run.created_at).toLocaleString() : ""].filter(Boolean).join(" · ");
    const active = run.status === "queued" || run.status === "in_progress";
    stop.disabled = !active || !ownerSession();
    link.href = run.html_url || "https://github.com/shayaanfarsheed-cmd/ULTRONAI/actions";
    link.hidden = !run.html_url;
    link.textContent = "Open workflow run ↗";
  }

  async function callControl(action, serverId) {
    const session = ownerSession();
    if (!session) throw new Error("Sign in with the configured owner account first.");
    if (!endpoint || endpoint.indexOf("/functions/v1/training-control") < 0) throw new Error("Training control endpoint is not configured.");
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": config.supabasePublishableKey || "",
        "Authorization": "Bearer " + session.access_token
      },
      body: JSON.stringify({ action: action, server_id: serverId })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Training control request failed (" + response.status + ").");
    return data;
  }

  async function refreshStatus() {
    if (busy) return;
    if (!ownerSession()) {
      setStatus(null);
      message("Owner sign-in is required. Public visitors cannot view private workflow activity or launch training.", "warn");
      return;
    }
    try {
      const result = await callControl("status");
      setStatus(result.run);
      message("", "");
    } catch (error) {
      message(error.message, "error");
    }
  }

  async function launch() {
    if (busy) return;
    const serverId = $("trainingServerSelect").value;
    if (serverId !== "github_actions_cpu") {
      message("That provider is manual-only. Choose GitHub Actions CPU for website launch.", "warn");
      return;
    }
    if (!window.confirm("Start ULTRON neural training on GitHub Actions CPU? This will use the configured training secrets and begin a real training session.")) return;
    busy = true;
    $("trainingStartButton").disabled = true;
    message("Submitting the owner-approved launch request…", "");
    try {
      const result = await callControl("start", serverId);
      message(result.message || "Launch request accepted.", "success");
      await refreshStatus();
    } catch (error) {
      message(error.message, "error");
    } finally {
      busy = false;
      $("trainingStartButton").disabled = !ownerSession();
    }
  }

  async function stop() {
    if (busy || !window.confirm("Cancel the currently queued or running ULTRON GitHub Actions workflow? The latest durable checkpoint will be retained if the training process has committed one.")) return;
    busy = true;
    $("trainingStopButton").disabled = true;
    try {
      const result = await callControl("stop");
      message(result.message || (result.stopped ? "Cancellation requested." : "No active run found."), "success");
      await refreshStatus();
    } catch (error) {
      message(error.message, "error");
    } finally {
      busy = false;
      await refreshStatus();
    }
  }

  async function loadServers() {
    const select = $("trainingServerSelect");
    if (!select) return;
    try {
      const response = await fetch("../servers.json", { cache: "no-store" });
      if (!response.ok) throw new Error("Server registry unavailable.");
      const data = await response.json();
      const servers = (data.servers || []).filter((server) => server.enabled !== false);
      select.innerHTML = servers.map((server) => {
        const remote = server.id === "github_actions_cpu";
        const label = String(server.name || server.id) + (remote ? " · REMOTE LAUNCH" : " · MANUAL ONLY");
        return '<option value="' + String(server.id).replace(/[^a-z0-9_-]/gi, "") + '">' + label.replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c])) + "</option>";
      }).join("");
      select.value = "github_actions_cpu";
    } catch (error) {
      message(error.message, "warn");
    }
  }

  function init() {
    if (!$("trainingStartButton")) return;
    $("trainingStartButton").addEventListener("click", launch);
    $("trainingStopButton").addEventListener("click", stop);
    $("trainingRefreshButton").addEventListener("click", refreshStatus);
    $("trainingServerSelect").addEventListener("change", function () {
      const canLaunch = $("trainingServerSelect").value === "github_actions_cpu" && Boolean(ownerSession());
      $("trainingStartButton").disabled = !canLaunch;
      message(canLaunch ? "" : "Selected provider is manual-only; open its provider page from the Servers section.", canLaunch ? "" : "warn");
    });
    window.addEventListener("ultron:owner-mode-changed", refreshStatus);
    loadServers().then(refreshStatus);
    if (pollTimer) window.clearInterval(pollTimer);
    pollTimer = window.setInterval(refreshStatus, 20000);
  }

  window.refreshTrainingControlStatus = refreshStatus;
  document.addEventListener("DOMContentLoaded", init);
})();
