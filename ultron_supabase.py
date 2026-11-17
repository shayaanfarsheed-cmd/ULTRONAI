from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


class SupabaseAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class LeaseLostError(RuntimeError):
    pass


@dataclass(frozen=True)
class LeaseResult:
    acquired: bool
    run_id: str
    lease_holder: str | None
    fencing_token: int | None
    lease_expires_at: str | None
    reason: str
    session_id: str | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    current = value or utc_now()
    return current.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class SupabaseRESTClient:
    def __init__(
        self,
        project_url: str,
        api_key: str,
        schema: str = "training_api",
        timeout_seconds: int = 20,
        opener: Any | None = None,
    ) -> None:
        if not project_url.startswith("https://"):
            raise ValueError("Supabase project URL must use HTTPS")
        if not api_key:
            raise ValueError("Supabase API key is required")
        if not schema.replace("_", "").isalnum():
            raise ValueError("Invalid PostgREST schema name")
        self.project_url = project_url.rstrip("/")
        self._api_key = api_key
        self.schema = schema
        self.timeout_seconds = timeout_seconds
        self._opener = opener or urllib.request.urlopen

    def __repr__(self) -> str:
        return f"SupabaseRESTClient(project_url={self.project_url!r}, schema={self.schema!r}, api_key=[redacted])"

    def request(
        self,
        method: str,
        table_or_path: str,
        query: Mapping[str, str] | None = None,
        body: Any | None = None,
        prefer: str | None = None,
        schema: str | None = None,
    ) -> Any:
        active_schema = schema or self.schema
        encoded_query = urllib.parse.urlencode(query or {}, safe="(),.*:")
        url = f"{self.project_url}/rest/v1/{table_or_path}"
        if encoded_query:
            url = f"{url}?{encoded_query}"
        headers = {
            "apikey": self._api_key,
            "Accept": "application/json",
        }
        if not self._api_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self._api_key}"
        if method.upper() in {"GET", "HEAD"}:
            headers["Accept-Profile"] = active_schema
        else:
            headers["Content-Profile"] = active_schema
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer
        payload = None if body is None else json.dumps(body, separators=(",", ":"), allow_nan=False).encode("utf-8")
        request = urllib.request.Request(url, data=payload, headers=headers, method=method.upper())
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
                if not raw:
                    return None
                content_type = response.headers.get("Content-Type", "")
                if "json" in content_type:
                    return json.loads(raw.decode("utf-8"))
                return raw
        except urllib.error.HTTPError as error:
            raw_error = error.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw_error)
                message = str(detail.get("message") or detail.get("hint") or "Supabase request failed")
                message = message.replace(self._api_key, "[redacted]")
                code = detail.get("code")
            except Exception:
                message = "Supabase request failed"
                code = None
            raise SupabaseAPIError(error.code, message, code) from None
        except urllib.error.URLError as error:
            reason = str(error.reason).replace(self._api_key, "[redacted]")
            raise SupabaseAPIError(0, f"Supabase connection failed: {reason}") from None

    def rpc(self, function: str, parameters: Mapping[str, Any]) -> dict[str, Any]:
        if not function.replace("_", "").isalnum():
            raise ValueError("Invalid RPC function name")
        result = self.request(
            "POST",
            f"rpc/{function}",
            body=dict(parameters),
            prefer="return=representation",
        )
        if isinstance(result, dict):
            return result
        if isinstance(result, list) and len(result) == 1 and isinstance(result[0], dict):
            return result[0]
        raise SupabaseAPIError(502, "Supabase RPC returned an unexpected response")

    def select(
        self,
        table: str,
        filters: Mapping[str, str] | None = None,
        columns: str = "*",
        limit: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        query = {"select": columns}
        query.update(filters or {})
        if limit is not None:
            query["limit"] = str(limit)
        if order:
            query["order"] = order
        result = self.request("GET", table, query=query)
        return result or []

    def insert(self, table: str, row: Mapping[str, Any]) -> list[dict[str, Any]]:
        result = self.request("POST", table, body=dict(row), prefer="return=representation")
        return result or []

    def patch(
        self,
        table: str,
        filters: Mapping[str, str],
        values: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        result = self.request(
            "PATCH",
            table,
            query=filters,
            body=dict(values),
            prefer="return=representation",
        )
        return result or []


class TrainingControlAPI:
    def __init__(self, client: SupabaseRESTClient, owner_id: str) -> None:
        self.client = client
        self.owner_id = owner_id

    def get_status(self, run_id: str) -> dict[str, Any] | None:
        rows = self.client.select("training_status", {"run_id": f"eq.{run_id}"}, limit=1)
        return rows[0] if rows else None

    def find_active_status(self) -> dict[str, Any] | None:
        rows = self.client.select(
            "training_status",
            {"owner_id": f"eq.{self.owner_id}"},
            limit=20,
            order="updated_at.desc",
        )
        for row in rows:
            if row.get("state") != "finished":
                return row
        return None

    def find_current_lease(self) -> dict[str, Any] | None:
        rows = self.client.select(
            "training_status",
            {
                "owner_id": f"eq.{self.owner_id}",
                "lease_holder": "not.is.null",
            },
            limit=1,
            order="updated_at.desc",
        )
        return rows[0] if rows else None


    def create_run_id(self) -> str:
        result = self.client.rpc(
            "get_or_create_active_run",
            {"p_owner_id": self.owner_id},
        )
        run_id = result.get("run_id")
        if not run_id:
            raise SupabaseAPIError(502, "Supabase did not return a training run ID")
        return str(run_id)

    def acquire_lease(
        self,
        run_id: str,
        server_name: str,
        lease_holder: str,
        ttl_seconds: int = 720,
        device: str = "cpu",
        session_limit_seconds: int | None = None,
    ) -> LeaseResult:
        if ttl_seconds < 60 or ttl_seconds > 3600:
            raise ValueError("Lease duration must be between 60 and 3600 seconds")
        result = self.client.rpc(
            "acquire_training_lease",
            {
                "p_run_id": run_id,
                "p_owner_id": self.owner_id,
                "p_server_id": server_name,
                "p_worker_id": lease_holder,
                "p_device": device,
                "p_session_limit_seconds": session_limit_seconds,
                "p_ttl_seconds": ttl_seconds,
            },
        )
        acquired = bool(result.get("granted"))
        return LeaseResult(
            acquired=acquired,
            run_id=str(result.get("run_id") or run_id),
            lease_holder=result.get("worker_id") or result.get("lease_holder"),
            fencing_token=int(result["fencing_token"]) if result.get("fencing_token") is not None else None,
            lease_expires_at=result.get("lease_expires_at"),
            reason="lease acquired" if acquired else str(result.get("reason") or "lease unavailable"),
            session_id=str(result["session_id"]) if result.get("session_id") else None,
        )

    def renew_lease(
        self,
        run_id: str,
        lease_holder: str,
        fencing_token: int,
        ttl_seconds: int = 720,
        status_values: Mapping[str, Any] | None = None,
    ) -> bool:
        if ttl_seconds < 60 or ttl_seconds > 3600:
            raise ValueError("Lease duration must be between 60 and 3600 seconds")
        values = dict(status_values or {})
        result = self.client.rpc(
            "heartbeat_training_lease",
            {
                "p_run_id": run_id,
                "p_owner_id": self.owner_id,
                "p_worker_id": lease_holder,
                "p_fencing_token": int(fencing_token),
                "p_ttl_seconds": ttl_seconds,
                "p_current_step": int(values.get("current_step", 0)),
                "p_loss": values.get("loss"),
                "p_learning_rate": values.get("learning_rate"),
                "p_current_topic": values.get("current_topic"),
                "p_difficulty": int(values.get("difficulty", 1)),
                "p_data_position": int(values.get("data_position", 0)),
                "p_data_epoch": int(values.get("data_epoch", 0)),
                "p_accuracy_by_topic": values.get("accuracy_by_topic") or {},
                "p_curriculum_state": values.get("curriculum_state") or {},
                "p_session_time_left_seconds": values.get("session_time_left_seconds"),
            },
        )
        return bool(result.get("ok"))

    def commit_checkpoint(
        self,
        run_id: str,
        lease_holder: str,
        fencing_token: int,
        checkpoint_id: str,
        checkpoint_size_bytes: int,
        training_state: Mapping[str, Any],
        manifest_sha256: str,
        ttl_seconds: int = 720,
    ) -> dict[str, Any]:
        if checkpoint_size_bytes < 1:
            raise ValueError("Checkpoint size must be positive")
        if len(manifest_sha256) != 64 or any(character not in "0123456789abcdef" for character in manifest_sha256):
            raise ValueError("Checkpoint manifest SHA-256 must be 64 lowercase hexadecimal characters")
        result = self.client.rpc(
            "commit_training_checkpoint",
            {
                "p_run_id": run_id,
                "p_owner_id": self.owner_id,
                "p_worker_id": lease_holder,
                "p_fencing_token": int(fencing_token),
                "p_checkpoint_id": checkpoint_id,
                "p_step": int(training_state["step"]),
                "p_size_bytes": int(checkpoint_size_bytes),
                "p_manifest_sha256": manifest_sha256,
                "p_current_topic": training_state.get("current_topic"),
                "p_difficulty": int(training_state.get("difficulty", 1)),
                "p_data_position": int(training_state.get("data_position", 0)),
                "p_data_epoch": int(training_state.get("data_epoch", 0)),
                "p_loss": training_state.get("loss"),
                "p_learning_rate": training_state.get("learning_rate"),
                "p_accuracy_by_topic": training_state.get("accuracy_by_topic") or {},
                "p_curriculum_state": training_state.get("curriculum_state") or {},
            },
        )
        if not result.get("ok"):
            raise LeaseLostError("Checkpoint pointer was not committed because the lease is no longer valid")
        return {
            "last_checkpoint_id": result.get("checkpoint_id"),
            "last_checkpoint_step": result.get("step"),
            "last_checkpoint_verified": result.get("verified"),
            "last_checkpoint_manifest_sha256": result.get("manifest_sha256"),
        }

    def release_lease(
        self,
        run_id: str,
        lease_holder: str,
        fencing_token: int,
        final_state: str = "handoff_needed",
        end_reason: str | None = None,
    ) -> bool:
        if final_state not in {"handoff_needed", "paused", "finished", "dead"}:
            raise ValueError("Invalid lease release state")
        reason_map = {
            "handoff_needed": "handoff",
            "paused": "user_stop",
            "finished": "finished",
            "dead": "crashed",
        }
        result = self.client.rpc(
            "release_training_lease",
            {
                "p_run_id": run_id,
                "p_owner_id": self.owner_id,
                "p_worker_id": lease_holder,
                "p_fencing_token": int(fencing_token),
                "p_end_reason": end_reason or reason_map[final_state],
                "p_final_state": final_state,
            },
        )
        return bool(result.get("ok"))

    def mark_dead_if_stale(self, run_id: str, stale_after_seconds: int = 720) -> bool:
        status = self.get_status(run_id)
        if status is None or status.get("state") == "finished":
            return False
        heartbeat = parse_timestamp(status.get("last_heartbeat_at"))
        expiry = parse_timestamp(status.get("lease_expires_at"))
        now = utc_now()
        if heartbeat is None or (now - heartbeat).total_seconds() < stale_after_seconds:
            return False
        if expiry is not None and expiry > now:
            return False
        filters = {
            "run_id": f"eq.{run_id}",
            "owner_id": f"eq.{self.owner_id}",
            "last_heartbeat_at": f"eq.{status.get('last_heartbeat_at')}",
        }
        filters["lease_expires_at"] = "is.null" if expiry is None else f"lt.{iso_utc(now)}"
        values = {"state": "dead", "updated_at": iso_utc(now)}
        return bool(self.client.patch("training_status", filters, values))
    def start_session(
        self,
        run_id: str,
        server_name: str,
        session_id: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> str:
        if session_id:
            return session_id
        status = self.get_status(run_id) or {}
        active_session_id = status.get("active_session_id")
        if active_session_id:
            return str(active_session_id)
        current_session = str(uuid.uuid4())
        self.client.insert(
            "server_log",
            {
                "owner_id": self.owner_id,
                "run_id": run_id,
                "session_id": current_session,
                "server_name": server_name,
                "started_at": iso_utc(),
                "gpu_seconds": 0,
                "manual": False,
                "details": dict(details or {}),
            },
        )
        return current_session
    def end_session(
        self,
        session_id: str,
        gpu_seconds: float,
        end_reason: str,
        details: Mapping[str, Any] | None = None,
    ) -> bool:
        if end_reason not in {"finished", "handoff", "quota", "kicked_out", "crashed", "user_stop", "unknown"}:
            raise ValueError("Invalid session end reason")
        filters = {
            "session_id": f"eq.{session_id}",
            "owner_id": f"eq.{self.owner_id}",
        }
        values = {
            "ended_at": iso_utc(),
            "gpu_seconds": max(0.0, float(gpu_seconds)),
            "end_reason": end_reason,
            "details": dict(details or {}),
        }
        return bool(self.client.patch("server_log", filters, values))

    def create_switch_request(
        self,
        run_id: str,
        from_server: str | None,
        to_server: str | None,
        reason: str,
        automatic: bool = False,
        idempotency_key: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        allowed = {
            "handoff_needed", "heartbeat_timeout", "quota", "no_gpu", "slow_gpu",
            "user_requested", "failed_start", "cpu_fallback", "server_unavailable",
            "server_available", "pause", "resume",
        }
        if reason not in allowed:
            raise ValueError("Invalid switch request reason")
        request_id = str(uuid.uuid4())
        row = {
            "id": request_id,
            "owner_id": self.owner_id,
            "run_id": run_id,
            "from_server": from_server,
            "to_server": to_server,
            "reason": reason,
            "requested_at": iso_utc(),
            "result": "waiting",
            "automatic": bool(automatic),
            "idempotency_key": idempotency_key or request_id,
            "metadata": dict(metadata or {}),
        }
        self.client.insert("switch_requests", row)
        return request_id

    def switch_requests_since(self, since_iso: str, limit: int = 200) -> list[dict[str, Any]]:
        return self.client.select(
            "switch_requests",
            {"owner_id": f"eq.{self.owner_id}", "requested_at": f"gte.{since_iso}"},
            limit=limit,
            order="requested_at.desc",
        )

    def server_logs_since(self, since_iso: str, limit: int = 1000) -> list[dict[str, Any]]:
        return self.client.select(
            "server_log",
            {"owner_id": f"eq.{self.owner_id}", "started_at": f"gte.{since_iso}"},
            limit=limit,
            order="started_at.desc",
        )

    def assign_switch_target(self, request_id: str, server_id: str, metadata: Mapping[str, Any] | None = None) -> bool:
        values: dict[str, Any] = {"to_server": server_id}
        if metadata is not None:
            values["metadata"] = dict(metadata)
        return bool(self.client.patch(
            "switch_requests",
            {"id": f"eq.{request_id}", "owner_id": f"eq.{self.owner_id}"},
            values,
        ))

    def mark_switch_requests_done(self, run_id: str, server_id: str) -> int:
        rows = self.client.select(
            "switch_requests",
            {
                "owner_id": f"eq.{self.owner_id}",
                "run_id": f"eq.{run_id}",
                "to_server": f"eq.{server_id}",
                "result": "in.(waiting,started)",
            },
            limit=50,
            order="requested_at.asc",
        )
        completed = 0
        for row in rows:
            if self.update_switch_request(
                str(row["id"]),
                "done",
                started_at=row.get("started_at") or iso_utc(),
                completed_at=iso_utc(),
            ):
                completed += 1
        return completed

    def update_server_status(
        self,
        run_id: str,
        server_id: str,
        status: str,
        reason: str | None = None,
        unavailable_until: str | None = None,
        kicked_out_until: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> bool:
        allowed = {"unknown", "ready", "running", "out_of_quota", "kicked_out", "unavailable_until"}
        if status not in allowed:
            raise ValueError("Invalid server status")
        row = self.get_status(run_id)
        if row is None:
            return False
        states = dict(row.get("server_statuses") or {})
        current = dict(states.get(server_id) or {})
        current["status"] = status
        current["updated_at"] = iso_utc()
        if reason is not None:
            current["reason"] = reason
        if unavailable_until is not None:
            current["unavailable_until"] = unavailable_until
        if kicked_out_until is not None:
            current["kicked_out_until"] = kicked_out_until
        if extra:
            current.update(dict(extra))
        states[server_id] = current
        return bool(self.client.patch(
            "training_status",
            {"run_id": f"eq.{run_id}", "owner_id": f"eq.{self.owner_id}"},
            {"server_statuses": states, "updated_at": iso_utc()},
        ))

    def waiting_switch_requests(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.client.select(
            "switch_requests",
            {"owner_id": f"eq.{self.owner_id}", "result": "eq.waiting"},
            limit=limit,
            order="requested_at.asc",
        )

    def update_switch_request(
        self,
        request_id: str,
        result: str,
        failure_reason: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        to_server: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> bool:
        if result not in {"waiting", "started", "failed", "done"}:
            raise ValueError("Invalid switch request result")
        values: dict[str, Any] = {"result": result}
        if failure_reason is not None:
            values["failure_reason"] = failure_reason
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        if to_server is not None:
            values["to_server"] = to_server
        if metadata is not None:
            values["metadata"] = dict(metadata)
        return bool(self.client.patch(
            "switch_requests",
            {"id": f"eq.{request_id}", "owner_id": f"eq.{self.owner_id}"},
            values,
        ))

    def request_handoff(self, run_id: str, handoff: bool = True) -> bool:
        return bool(self.client.patch(
            "training_status",
            {"run_id": f"eq.{run_id}", "owner_id": f"eq.{self.owner_id}"},
            {"handoff_requested": bool(handoff), "updated_at": iso_utc()},
        ))

    def controls(self, run_id: str) -> dict[str, Any]:
        status = self.get_status(run_id)
        if status is None:
            return {
                "pause_requested": False,
                "handoff_requested": False,
                "automatic_start_enabled": False,
                "server_statuses": {},
            }
        return {
            "pause_requested": bool(status.get("pause_requested")),
            "handoff_requested": bool(status.get("handoff_requested")),
            "automatic_start_enabled": bool(status.get("automatic_start_enabled")),
            "server_statuses": status.get("server_statuses") or {},
        }


def from_environment() -> TrainingControlAPI:
    project_url = os.environ.get("SUPABASE_URL", "").strip()
    secret_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    owner_id = os.environ.get("SUPABASE_OWNER_ID", "").strip()
    if not project_url or not secret_key or not owner_id:
        raise RuntimeError("Set SUPABASE_URL, SUPABASE_SECRET_KEY and SUPABASE_OWNER_ID in the provider's secret manager")
    if not secret_key.startswith("sb_secret_"):
        raise RuntimeError("SUPABASE_SECRET_KEY must be a current sb_secret_ key; never use a publishable key for training")
    try:
        uuid.UUID(owner_id)
    except ValueError:
        raise RuntimeError("SUPABASE_OWNER_ID must be the UUID of your Supabase Auth account") from None
    client = SupabaseRESTClient(project_url, secret_key)
    return TrainingControlAPI(client, owner_id)
