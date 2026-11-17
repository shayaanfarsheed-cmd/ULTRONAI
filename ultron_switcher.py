from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ultron_supabase import TrainingControlAPI, from_environment, iso_utc, parse_timestamp, utc_now


def _as_utc(value: datetime | None = None) -> datetime:
    result = value or utc_now()
    if result.tzinfo is None:
        return result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _period_start(period: str, now: datetime) -> datetime | None:
    now = _as_utc(now)
    if period == "weekly":
        return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def calculate_quota_usage(
    servers: Sequence[Mapping[str, Any]],
    logs: Sequence[Mapping[str, Any]],
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    now = _as_utc(now)
    result: dict[str, dict[str, Any]] = {}
    for server in servers:
        server_id = str(server["id"])
        name = str(server.get("name", server_id))
        limits = server.get("limits", {})
        period = str(limits.get("quota_period", "unknown"))
        limit_hours = (
            limits.get("weekly_gpu_hours_baseline")
            or limits.get("monthly_gpu_hours")
            or limits.get("quota_hours")
        )
        start = _period_start(period, now)
        used_seconds = 0.0
        if start is not None:
            for log in logs:
                details = log.get("details") or {}
                log_server_id = details.get("server_id")
                if log_server_id and str(log_server_id) != server_id:
                    continue
                if not log_server_id and str(log.get("server_name")) != name:
                    continue
                started = parse_timestamp(log.get("started_at"))
                if started is None or started < start:
                    continue
                seconds = float(log.get("gpu_seconds") or 0)
                if log.get("ended_at") is None and (details.get("compute_device") or details.get("device")) == "cuda":
                    seconds = max(seconds, (now - started).total_seconds())
                used_seconds += max(0.0, seconds)
        used_hours = used_seconds / 3600.0
        if limit_hours is None or start is None:
            percent = None
            numeric_limit = None
        else:
            numeric_limit = float(limit_hours)
            percent = (used_hours / numeric_limit * 100.0) if numeric_limit > 0 else 100.0
        result[server_id] = {
            "server_id": server_id,
            "used_hours": round(used_hours, 3),
            "limit_hours": numeric_limit,
            "usage_percent": round(percent, 1) if percent is not None else None,
            "period": period,
            "period_start": iso_utc(start) if start else None,
            "warning": percent is not None and percent >= 80,
        }
    return result


def _status_for(server: Mapping[str, Any], statuses: Mapping[str, Any], now: datetime) -> str:
    server_id = str(server["id"])
    entry = dict(statuses.get(server_id) or {})
    status = str(entry.get("status") or server.get("current_status") or "unknown")
    until = parse_timestamp(entry.get("unavailable_until") or entry.get("kicked_out_until"))
    if status in {"unavailable_until", "kicked_out"} and until is not None and until <= now:
        return "unknown"
    reset_at = parse_timestamp(entry.get("quota_reset_at"))
    if status == "out_of_quota" and reset_at is not None and reset_at <= now:
        return "unknown"
    return status


def select_next_server(
    servers: Sequence[Mapping[str, Any]],
    statuses: Mapping[str, Any],
    quota_usage: Mapping[str, Any],
    threshold_percent: float = 90.0,
    fallback_server_id: str = "github_actions_cpu",
    exclude_server_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    now = _as_utc(now)
    ordered = sorted(servers, key=lambda item: int(item.get("order", 999)))
    eligible: list[dict[str, Any]] = []
    for server in ordered:
        server_id = str(server["id"])
        if server_id == exclude_server_id or not bool(server.get("enabled", True)):
            continue
        status = _status_for(server, statuses, now)
        quota = dict(quota_usage.get(server_id) or {})
        percent = quota.get("usage_percent")
        if status in {"running", "out_of_quota", "kicked_out", "unavailable_until"}:
            continue
        if percent is not None and float(percent) >= threshold_percent:
            continue
        if status == "ready":
            eligible.append({
                "server": dict(server),
                "status": status,
                "quota": quota,
                "requires_manual_check": False,
            })
    if eligible:
        return eligible[0]

    fallback = next((item for item in ordered if item.get("id") == fallback_server_id), None)
    if fallback is not None and fallback.get("id") != exclude_server_id and bool(fallback.get("enabled", True)):
        status = _status_for(fallback, statuses, now)
        quota = dict(quota_usage.get(fallback_server_id) or {})
        percent = quota.get("usage_percent")
        if status not in {"running", "out_of_quota", "kicked_out", "unavailable_until"} and (
            percent is None or float(percent) < threshold_percent
        ):
            return {
                "server": dict(fallback),
                "status": status,
                "quota": quota,
                "requires_manual_check": status != "ready",
            }
    return None


def build_start_instruction(server: Mapping[str, Any], requires_manual_check: bool = False) -> str:
    server_id = str(server.get("id"))
    instructions = {
        "kaggle": "Open Kaggle, open the ULTRON Training Control notebook, then press Run All.",
        "google_colab": "Open Colab, choose a free GPU if one is available, then select Runtime > Run all.",
        "lightning_ai": "Open Lightning AI, open your free Studio, verify the selected hardware is free, then run the notebook.",
        "github_actions_cpu": "Open GitHub Actions, select ULTRON CPU Training, then press Run workflow.",
        "huggingface_cpu": "Open your CPU Basic Space, start it, then launch the ULTRON training notebook.",
    }
    instruction = instructions.get(server_id, f"Open {server.get('name', server_id)} and start the ULTRON notebook.")
    if requires_manual_check:
        instruction = "Check that the free quota and hardware are available, mark this server Ready, then " + instruction[0].lower() + instruction[1:]
    return instruction


def launch_kaggle_kernel(repository_root: str | Path, environment: Mapping[str, str] | None = None) -> bool:
    env = dict(os.environ if environment is None else environment)
    username = env.get("KAGGLE_USERNAME", "").strip()
    key = env.get("KAGGLE_KEY", "").strip()
    slug = env.get("KAGGLE_KERNEL_SLUG", "ultron-training-control").strip()
    if not username or not key or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,49}", username):
        return False
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,49}", slug):
        return False
    root = Path(repository_root)
    notebook = root / "train.ipynb"
    if not notebook.is_file():
        return False
    with tempfile.TemporaryDirectory(prefix="ultron-kaggle-") as temporary:
        folder = Path(temporary)
        (folder / "train.ipynb").write_bytes(notebook.read_bytes())
        metadata = {
            "id": f"{username}/{slug}",
            "title": "ULTRON Training Control",
            "code_file": "train.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": True,
            "enable_gpu": True,
            "enable_internet": True,
        }
        (folder / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        try:
            result = subprocess.run(
                ["kaggle", "kernels", "push", "-p", str(folder)],
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
                check=False,
            )
        except Exception:
            return False
        return result.returncode == 0


def dispatch_github_workflow(
    repository: str,
    workflow_file: str,
    ref: str = "main",
    token: str | None = None,
    opener: Any | None = None,
) -> bool:
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        return False
    if "/" in workflow_file or ".." in workflow_file:
        return False
    url = f"https://api.github.com/repos/{repository}/actions/workflows/{workflow_file}/dispatches"
    request = urllib.request.Request(
        url,
        data=json.dumps({"ref": ref}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with (opener or urllib.request.urlopen)(request, timeout=30) as response:
            return response.status in {201, 204}
    except urllib.error.HTTPError as error:
        return error.code in {201, 204}
    except Exception:
        return False


def _auto_start_allowed(
    server: Mapping[str, Any],
    server_status: Mapping[str, Any],
    status_row: Mapping[str, Any],
    config: Mapping[str, Any],
    recent_requests: Sequence[Mapping[str, Any]],
    now: datetime,
    environment: Mapping[str, str],
) -> tuple[bool, str]:
    switching = config.get("switching", {})
    if not bool(status_row.get("automatic_start_enabled")):
        return False, "Automatic start is disabled on the dashboard."
    if not bool(switching.get("automatic_switching_enabled", True)):
        return False, "Automatic switching is disabled in config.json."
    if server_status.get("status") != "ready":
        return False, "The target server has not been marked Ready."
    capability = str(server.get("automatic_start", "no"))
    if capability != "yes":
        return False, "This provider is configured for guided switching only."
    allowed = set(switching.get("platform_allowlist", []))
    if server.get("id") not in allowed:
        return False, "This server is not on the automatic-start allowlist."
    starts = [
        row for row in recent_requests
        if row.get("automatic") and row.get("result") in {"started", "done", "failed"}
    ]
    max_per_day = int(switching.get("maximum_automatic_starts_per_day", 3))
    if len(starts) >= max_per_day:
        return False, "Daily automatic-start safety limit reached."
    cooldown = int(switching.get("cooldown_between_automatic_starts_seconds", switching.get("automatic_start_cooldown_seconds", 1200)))
    timestamps = [parse_timestamp(row.get("started_at") or row.get("requested_at")) for row in starts]
    timestamps = [item for item in timestamps if item is not None]
    if timestamps and (now - max(timestamps)).total_seconds() < cooldown:
        return False, "Automatic-start cooldown is still active."
    if server.get("id") == "kaggle":
        required = ("KAGGLE_USERNAME", "KAGGLE_KEY")
        if any(not environment.get(name) for name in required):
            return False, "Kaggle API credentials are not configured in GitHub Actions secrets."
    if server.get("id") == "github_actions_cpu":
        if not (environment.get("GITHUB_TOKEN") or environment.get("GH_TOKEN")):
            return False, "GitHub workflow dispatch token is unavailable."
    return True, "Automatic start passed the safety checks."


def run_switcher(
    config: Mapping[str, Any],
    servers_registry: Mapping[str, Any],
    api: TrainingControlAPI | None = None,
    repository_root: str | Path = ".",
    environment: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    api = api or from_environment()
    env = dict(os.environ if environment is None else environment)
    now = _as_utc(now)
    status = api.find_active_status()
    if status is None:
        return {"state": "no_active_run", "instruction": "Open the training notebook when you are ready to begin."}
    run_id = str(status["run_id"])
    monitoring = config.get("monitoring", {})
    stale_after = int(monitoring.get("stale_run_after_seconds", 720))
    api.mark_dead_if_stale(run_id, stale_after)
    status = api.get_status(run_id) or status

    servers = servers_registry.get("servers", [])
    server_statuses = status.get("server_statuses") or {}
    logs = api.server_logs_since(iso_utc(now - timedelta(days=35)))
    quota_usage = calculate_quota_usage(servers, logs, now)
    threshold = float(config.get("switching", {}).get(
        "quota_switch_threshold_percent",
        config.get("quota_management", {}).get("switch_at_percent", 90),
    ))

    current_server = next(
        (item for item in servers if item.get("name") == status.get("current_server")),
        None,
    )
    current_server_id = str(current_server.get("id")) if current_server else None
    current_quota = quota_usage.get(current_server_id or "", {})
    if status.get("state") == "paused" and status.get("pause_requested"):
        return {"state": "paused", "instruction": "Training is paused. Press Resume on the dashboard when you want to continue."}
    if status.get("state") == "running" and current_server_id and current_quota.get("usage_percent") is not None:
        if float(current_quota["usage_percent"]) >= threshold:
            api.create_switch_request(
                run_id,
                current_server_id,
                None,
                "quota",
                automatic=False,
                metadata={"usage_percent": current_quota["usage_percent"]},
            )
            api.request_handoff(run_id, True)
            return {
                "state": "handoff_requested",
                "reason": "quota",
                "usage_percent": current_quota["usage_percent"],
                "instruction": "ULTRON is saving a checkpoint and handing off because this server is near its quota.",
            }

    expiry = parse_timestamp(status.get("lease_expires_at"))
    lease_valid = expiry is not None and expiry > now
    heartbeat = parse_timestamp(status.get("last_heartbeat_at"))
    heartbeat_fresh = heartbeat is not None and (now - heartbeat).total_seconds() <= stale_after
    recent = api.switch_requests_since(iso_utc(now - timedelta(days=1)))
    started_timeout = int(config.get("switching", {}).get("failed_start_timeout_seconds", 1200))
    retry_cooldown = int(config.get("switching", {}).get("failed_server_cooldown_seconds", 21600))
    failed_request = None
    for request in recent:
        if request.get("result") != "started" or not request.get("started_at"):
            continue
        started_at = parse_timestamp(request["started_at"])
        target_server = next((item for item in servers if item.get("id") == request.get("to_server")), None)
        if (
            target_server is not None
            and status.get("state") == "running"
            and status.get("current_server") == target_server.get("name")
            and heartbeat is not None
            and started_at is not None
            and heartbeat >= started_at
        ):
            api.update_switch_request(str(request["id"]), "done", completed_at=iso_utc(now))
            continue
        if started_at and (now - started_at).total_seconds() > started_timeout:
            failed_request = request
            break

    if status.get("state") == "running" and heartbeat_fresh:
        return {"state": "running", "instruction": f"Running on {status.get('current_server')}. Nothing to do."}
    if lease_valid:
        return {
            "state": "waiting_for_lease",
            "instruction": "The previous server still holds the training lease. Wait for it to stop before starting another.",
            "lease_expires_at": status.get("lease_expires_at"),
        }
    if status.get("state") == "finished":
        return {"state": "finished", "instruction": "Training has finished. Review the evaluation results."}

    if failed_request:
        failed_server_id = failed_request.get("to_server")
        api.update_switch_request(
            str(failed_request["id"]),
            "failed",
            failure_reason="No first heartbeat arrived before the configured timeout.",
        )
        if failed_server_id:
            api.update_server_status(
                run_id,
                str(failed_server_id),
                "kicked_out",
                reason="No first heartbeat after automatic start.",
                kicked_out_until=iso_utc(now + timedelta(seconds=retry_cooldown)),
            )
        api.create_switch_request(
            run_id,
            current_server_id,
            None,
            "failed_start",
            automatic=False,
            metadata={"failed_server_id": failed_server_id},
        )

    waiting = api.waiting_switch_requests(limit=20)
    if not waiting:
        reason = "heartbeat_timeout" if status.get("state") == "dead" else "handoff_needed"
        request_id = api.create_switch_request(
            run_id,
            current_server_id,
            None,
            reason,
            automatic=False,
            metadata={"state": status.get("state")},
        )
        waiting = [{"id": request_id, "run_id": run_id, "from_server": current_server_id, "to_server": None, "result": "waiting"}]
    request_row = waiting[0]

    decision = select_next_server(
        servers,
        server_statuses,
        quota_usage,
        threshold_percent=threshold,
        fallback_server_id=str(config.get("server_rotation", {}).get("fallback_server_id", "github_actions_cpu")),
        exclude_server_id=current_server_id,
        now=now,
    )
    if decision is None:
        return {
            "state": "no_server_available",
            "instruction": "All listed servers are unavailable. Check the server list and mark a free server Ready when it becomes available.",
            "quota_usage": quota_usage,
        }

    target = decision["server"]
    target_id = str(target["id"])
    api.assign_switch_target(
        str(request_row["id"]),
        target_id,
        {
            "selected_at": iso_utc(now),
            "quota_usage": decision["quota"],
            "requires_manual_check": decision["requires_manual_check"],
        },
    )
    instruction = build_start_instruction(target, decision["requires_manual_check"])
    target_status = dict(server_statuses.get(target_id) or {})

    recent = api.switch_requests_since(iso_utc(now - timedelta(days=1)))
    allowed, auto_reason = _auto_start_allowed(
        target,
        target_status,
        status,
        config,
        recent,
        now,
        env,
    )
    if not allowed:
        return {
            "state": "guided_switch",
            "request_id": request_row["id"],
            "target_server": target_id,
            "target_name": target.get("name"),
            "open_url": target.get("notebook_open_url") or target.get("notebook_url"),
            "instruction": instruction,
            "automatic_start_reason": auto_reason,
            "quota_usage": quota_usage,
        }

    api.update_switch_request(
        str(request_row["id"]),
        "started",
        started_at=iso_utc(now),
        to_server=target_id,
        metadata={"automatic": True, "provider": target.get("provider")},
    )
    if target_id == "kaggle":
        launched = launch_kaggle_kernel(repository_root, env)
    elif target_id == "github_actions_cpu":
        launched = dispatch_github_workflow(
            repository=str(env.get("GITHUB_REPOSITORY", "shayaanfarsheed-cmd/ULTRONAI")),
            workflow_file="cpu-training.yml",
            ref=str(env.get("GITHUB_REF_NAME", "main")),
            token=env.get("GITHUB_TOKEN") or env.get("GH_TOKEN"),
        )
    else:
        launched = False

    if not launched:
        api.update_switch_request(
            str(request_row["id"]),
            "failed",
            failure_reason="The official provider launch command failed.",
        )
        api.update_server_status(
            run_id,
            target_id,
            "kicked_out",
            reason="Automatic launch failed.",
            kicked_out_until=iso_utc(now + timedelta(seconds=retry_cooldown)),
        )
        return {
            "state": "automatic_start_failed",
            "target_server": target_id,
            "instruction": "Automatic start failed. Open the server manually and press Run All.",
            "open_url": target.get("notebook_open_url") or target.get("notebook_url"),
        }
    return {
        "state": "automatic_start_started",
        "target_server": target_id,
        "instruction": f"Started {target.get('name')}. Waiting for its first heartbeat before marking the switch complete.",
        "request_id": request_row["id"],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--servers", default="servers.json")
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    servers = json.loads(Path(args.servers).read_text(encoding="utf-8"))
    configured_url = config.get("database", {}).get("project_url")
    if configured_url and not os.environ.get("SUPABASE_URL"):
        os.environ["SUPABASE_URL"] = str(configured_url)
    result = run_switcher(config, servers, repository_root=args.repository_root)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
