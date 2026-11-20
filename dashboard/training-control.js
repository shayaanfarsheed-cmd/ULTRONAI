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

  function setStatus(run, serverId) {
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
    label.textContent = String(run.status || "unknown").replace(/^KernelWorkerStatus\./, "").replace(/_/g, " ").toUpperCase();
    details.textContent = [run.message || run.conclusion || "No conclusion yet", run.created_at ? new Date(run.created_at).toLocaleString() : ""].filter(Boolean).join(" · ");
    $("trainingStartButton").disabled = !ownerSession();
    const active = run.status === "queued" || run.status === "in_progress";
    stop.hidden = false;
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
    const startButton = $("trainingStartButton");
    const selectedServer = $("trainingServerSelect").value;
    const canRemoteLaunch = selectedServer === "github_actions_cpu";
    if (startButton) startButton.disabled = !ownerSession() || !canRemoteLaunch;
    $("trainingStopButton").hidden = false;
    $("trainingStatusTitle").textContent = "GitHub Actions CPU";
    $("trainingServerHelp").textContent = "GitHub Actions CPU runs a safe remote compute diagnostic. It does not train ULTRON. Google Colab remains a separate manual-only option.";
    if (busy) return;
    if (selectedServer !== "github_actions_cpu") {
      setStatus(null, selectedServer);
      message("Google Colab is manual-only. Remote status and Start/Stop controls are available for GitHub Actions CPU.", "warn");
      return;
    }
    if (!ownerSession()) {
      setStatus(null);
      message("Owner sign-in is required. Public visitors cannot view private workflow activity or launch training.", "warn");
      return;
    }
    try {
      const result = await callControl("status", selectedServer);
      setStatus(result.run, selectedServer);
      message("", "");
    } catch (error) {
      message(error.message, "error");
    }
  }

  async function launch() {
    if (busy) return;
    const serverId = $("trainingServerSelect").value;
    if (serverId !== "github_actions_cpu") {
      message("That provider does not have a remote launch adapter yet.", "warn");
      return;
    }
    const confirmation = "Start a safe CPU compute diagnostic on GitHub Actions? It installs Python dependencies and CPU-only PyTorch, measures runner resources, and does not start model training or touch checkpoints.";
    if (!window.confirm(confirmation)) return;
    busy = true;
    $("trainingStartButton").disabled = true;
    message("Submitting the owner-approved launch request…", "");
    try {
      const result = await callControl("start", serverId);
      message(result.message || "Diagnostic request accepted.", "success");
    } catch (error) {
      message(error.message, "error");
    } finally {
      busy = false;
      $("trainingStartButton").disabled = !ownerSession() || $("trainingServerSelect").value !== "github_actions_cpu";
    }
    // Refresh only after clearing busy; refreshStatus intentionally exits while a
    // control request is active.
    await refreshStatus();
  }

  async function stop() {
    const selectedServer = $("trainingServerSelect").value;
    const confirmation = "Cancel the currently queued or running ULTRON CPU diagnostic? This diagnostic does not train the model or create, modify, or delete checkpoints.";
    if (busy || !window.confirm(confirmation)) return;
    busy = true;
    $("trainingStopButton").disabled = true;
    try {
      const result = await callControl("stop", $("trainingServerSelect").value);
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
        const label = String(server.name || server.id) + (remote ? " · OWNER REMOTE LAUNCH" : " · MANUAL ONLY");
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
      $("trainingStopButton").hidden = false;
      $("trainingStatusTitle").textContent = "GitHub Actions CPU";
      $("trainingServerHelp").textContent = "GitHub Actions CPU runs a safe remote compute diagnostic. It does not train ULTRON. Google Colab remains a separate manual-only option.";
      message(canLaunch ? "" : "Selected provider is manual-only; open its provider page from the Servers section.", canLaunch ? "" : "warn");
      refreshStatus();
    });
    window.addEventListener("ultron:owner-mode-changed", refreshStatus);
    loadServers().then(refreshStatus);
    if (pollTimer) window.clearInterval(pollTimer);
    pollTimer = window.setInterval(refreshStatus, 60000);
  }

  window.refreshTrainingControlStatus = refreshStatus;
  document.addEventListener("DOMContentLoaded", init);
})();
