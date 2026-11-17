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
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }
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
                code = detail.get("code")
            except Exception:
                message = "Supabase request failed"
                code = None
            raise SupabaseAPIError(error.code, message, code) from None
        except urllib.error.URLError as error:
            raise SupabaseAPIError(0, f"Supabase connection failed: {error.reason}") from None

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
        active = self.find_active_status()
        if active is not None:
            return str(active["run_id"])
        return str(uuid.uuid4())

    def acquire_lease(
        self,
        run_id: str,
        server_name: str,
        lease_holder: str,
        ttl_seconds: int = 720,
    ) -> LeaseResult:
        if ttl_seconds < 60:
            raise ValueError("Lease duration must be at least 60 seconds")
        now = utc_now()
        now_text = iso_utc(now)
        expiry_text = iso_utc(now + timedelta(seconds=ttl_seconds))
        status = self.get_status(run_id)

        if status is None:
            other_lease = self.find_current_lease()
            if other_lease is not None and other_lease.get("run_id") != run_id:
                return LeaseResult(
                    False,
                    str(other_lease["run_id"]),
                    other_lease.get("lease_holder"),
                    int(other_lease.get("fencing_token") or 0),
                    other_lease.get("lease_expires_at"),
                    "another run already owns this account's training lease",
                )
            row = {
                "run_id": run_id,
                "owner_id": self.owner_id,
                "current_server": server_name,
                "state": "starting",
                "lease_holder": lease_holder,
                "lease_expires_at": expiry_text,
                "fencing_token": 1,
                "last_heartbeat_at": now_text,
                "session_started_at": now_text,
                "updated_at": now_text,
            }
            try:
                created = self.client.insert("training_status", row)
            except SupabaseAPIError as error:
                if error.status_code == 409 or error.code == "23505":
                    other_lease = self.find_current_lease()
                    if other_lease is not None:
                        return LeaseResult(
                            False,
                            str(other_lease["run_id"]),
                            other_lease.get("lease_holder"),
                            int(other_lease.get("fencing_token") or 0),
                            other_lease.get("lease_expires_at"),
                            "another worker acquired the account lease first",
                        )
                raise
            if created:
                return LeaseResult(True, run_id, lease_holder, 1, expiry_text, "lease acquired for new run")
            return LeaseResult(False, run_id, None, None, None, "status row creation returned no row")

        if status.get("owner_id") != self.owner_id:
            raise SupabaseAPIError(403, "Run belongs to a different owner")
        if status.get("state") == "finished":
            return LeaseResult(False, run_id, status.get("lease_holder"), int(status.get("fencing_token") or 0), status.get("lease_expires_at"), "run is already finished")
        if status.get("pause_requested"):
            return LeaseResult(False, run_id, status.get("lease_holder"), int(status.get("fencing_token") or 0), status.get("lease_expires_at"), "pause has been requested")

        current_holder = status.get("lease_holder")
        current_expiry = parse_timestamp(status.get("lease_expires_at"))
        current_token = int(status.get("fencing_token") or 0)

        if current_holder == lease_holder and current_expiry is not None and current_expiry > now:
            renewed = self.renew_lease(run_id, lease_holder, current_token, ttl_seconds)
            if renewed:
                return LeaseResult(True, run_id, lease_holder, current_token, expiry_text, "existing lease renewed")

        if current_expiry is not None and current_expiry > now:
            return LeaseResult(
                False,
                run_id,
                current_holder,
                current_token,
                status.get("lease_expires_at"),
                "another worker still holds a valid lease",
            )

        filters = {
            "run_id": f"eq.{run_id}",
            "owner_id": f"eq.{self.owner_id}",
            "fencing_token": f"eq.{current_token}",
        }
        if current_expiry is None:
            filters["lease_expires_at"] = "is.null"
        else:
            filters["lease_expires_at"] = f"lt.{now_text}"
        new_token = current_token + 1
        values = {
            "lease_holder": lease_holder,
            "lease_expires_at": expiry_text,
            "fencing_token": new_token,
            "current_server": server_name,
            "state": "running",
            "last_heartbeat_at": now_text,
            "session_started_at": now_text,
            "updated_at": now_text,
        }
        updated = self.client.patch("training_status", filters, values)
        if updated:
            return LeaseResult(True, run_id, lease_holder, new_token, expiry_text, "expired lease taken over with a new fencing token")
        latest = self.get_status(run_id) or {}
        return LeaseResult(
            False,
            run_id,
            latest.get("lease_holder"),
            int(latest.get("fencing_token") or 0),
            latest.get("lease_expires_at"),
            "lease compare-and-set lost a race; this worker must wait",
        )

    def renew_lease(
        self,
        run_id: str,
        lease_holder: str,
        fencing_token: int,
        ttl_seconds: int = 720,
        status_values: Mapping[str, Any] | None = None,
    ) -> bool:
        now = utc_now()
        now_text = iso_utc(now)
        expiry_text = iso_utc(now + timedelta(seconds=ttl_seconds))
        filters = {
            "run_id": f"eq.{run_id}",
            "owner_id": f"eq.{self.owner_id}",
            "lease_holder": f"eq.{lease_holder}",
            "fencing_token": f"eq.{fencing_token}",
            "lease_expires_at": f"gt.{now_text}",
        }
        values = {
            "lease_expires_at": expiry_text,
            "last_heartbeat_at": now_text,
            "updated_at": now_text,
        }
        values.update(dict(status_values or {}))
        return bool(self.client.patch("training_status", filters, values))

    def commit_checkpoint(
        self,
        run_id: str,
        lease_holder: str,
        fencing_token: int,
        checkpoint_id: str,
        checkpoint_size_bytes: int,
        training_state: Mapping[str, Any],
        ttl_seconds: int = 720,
    ) -> dict[str, Any]:
        if checkpoint_size_bytes < 1:
            raise ValueError("Checkpoint size must be positive")
        now = utc_now()
        now_text = iso_utc(now)
        expiry_text = iso_utc(now + timedelta(seconds=ttl_seconds))
        filters = {
            "run_id": f"eq.{run_id}",
            "owner_id": f"eq.{self.owner_id}",
            "lease_holder": f"eq.{lease_holder}",
            "fencing_token": f"eq.{fencing_token}",
            "lease_expires_at": f"gt.{now_text}",
        }
        values = {
            "current_step": int(training_state["step"]),
            "current_topic": str(training_state["current_topic"]),
            "difficulty": int(training_state["difficulty"]),
            "data_position": int(training_state["data_position"]),
            "data_epoch": int(training_state.get("data_epoch", 0)),
            "loss": training_state.get("loss"),
            "accuracy_by_topic": training_state.get("accuracy_by_topic", {}),
            "curriculum_state": training_state.get("curriculum_state", {}),
            "learning_rate": training_state.get("learning_rate"),
            "last_checkpoint_id": checkpoint_id,
            "last_checkpoint_step": int(training_state["step"]),
            "last_checkpoint_at": now_text,
            "last_checkpoint_size_bytes": checkpoint_size_bytes,
            "last_checkpoint_verified": True,
            "last_heartbeat_at": now_text,
            "lease_expires_at": expiry_text,
            "updated_at": now_text,
            "state": "running",
        }
        updated = self.client.patch("training_status", filters, values)
        if not updated:
            raise LeaseLostError("Checkpoint pointer was not committed because this worker no longer owns the lease")
        return updated[0]

    def release_lease(
        self,
        run_id: str,
        lease_holder: str,
        fencing_token: int,
        final_state: str = "handoff_needed",
    ) -> bool:
        if final_state not in {"handoff_needed", "paused", "finished", "dead"}:
            raise ValueError("Invalid lease release state")
        filters = {
            "run_id": f"eq.{run_id}",
            "owner_id": f"eq.{self.owner_id}",
            "lease_holder": f"eq.{lease_holder}",
            "fencing_token": f"eq.{fencing_token}",
        }
        values = {
            "lease_holder": None,
            "lease_expires_at": None,
            "state": final_state,
            "updated_at": iso_utc(),
        }
        return bool(self.client.patch("training_status", filters, values))

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
        observed_heartbeat = status.get("last_heartbeat_at")
        filters = {
            "run_id": f"eq.{run_id}",
            "owner_id": f"eq.{self.owner_id}",
            "last_heartbeat_at": f"eq.{observed_heartbeat}",
            "lease_expires_at": f"lt.{iso_utc(now)}",
        }
        values = {"state": "dead", "updated_at": iso_utc(now)}
        return bool(self.client.patch("training_status", filters, values))

    def start_session(self, run_id: str, server_name: str, session_id: str | None = None) -> str:
        current_session = session_id or str(uuid.uuid4())
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
                "details": {},
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
        return bool(self.client.patch(
            "switch_requests",
            {"id": f"eq.{request_id}", "owner_id": f"eq.{self.owner_id}"},
            values,
        ))

    def controls(self, run_id: str) -> dict[str, Any]:
        status = self.get_status(run_id)
        if status is None:
            return {"pause_requested": False, "automatic_start_enabled": False, "server_statuses": {}}
        return {
            "pause_requested": bool(status.get("pause_requested")),
            "automatic_start_enabled": bool(status.get("automatic_start_enabled")),
            "server_statuses": status.get("server_statuses") or {},
        }


def from_environment() -> TrainingControlAPI:
    project_url = os.environ.get("SUPABASE_URL", "").strip()
    secret_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    owner_id = os.environ.get("SUPABASE_OWNER_ID", "").strip()
    if not project_url or not secret_key or not owner_id:
        raise RuntimeError("Set SUPABASE_URL, SUPABASE_SECRET_KEY and SUPABASE_OWNER_ID in the provider's secret manager")
    client = SupabaseRESTClient(project_url, secret_key)
    return TrainingControlAPI(client, owner_id)
