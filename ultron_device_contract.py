"""Pure local validation for the ULTRON device command contract.

This module validates command shape and time/fencing policy. It does not
authenticate a device, establish ownership, persist replay state, or replace
authoritative server-side transaction checks.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Collection

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schemas" / "device-command.schema.json"
MAX_COMMAND_TTL = timedelta(seconds=120)
MAX_FUTURE_ISSUED_AT = timedelta(seconds=30)
RUN_ACTIONS = frozenset({"start", "pause", "resume", "stop"})


def _load_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


_VALIDATOR = _load_validator()


def _parse_timestamp(value: str, field: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_command(
    command: dict[str, Any],
    *,
    now: datetime | None = None,
    current_fencing_token: int | None = None,
    seen_nonces: Collection[str] | None = None,
) -> None:
    """Raise ValueError unless a command passes schema and dynamic policy.

    In production, fencing and replay state must come from an authoritative,
    current server source. A local cache alone cannot authorize execution.
    """
    errors = sorted(
        _VALIDATOR.iter_errors(command),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    if errors:
        detail = "; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"Invalid command schema: {detail}")

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    current_time = current_time.astimezone(timezone.utc)

    issued_at = _parse_timestamp(command["issued_at"], "issued_at")
    expires_at = _parse_timestamp(command["expires_at"], "expires_at")

    if issued_at > current_time + MAX_FUTURE_ISSUED_AT:
        raise ValueError("command issued_at is too far in the future")
    if expires_at <= issued_at:
        raise ValueError("expires_at must be later than issued_at")
    if expires_at - issued_at > MAX_COMMAND_TTL:
        raise ValueError("command lifetime exceeds 120 seconds")
    if expires_at <= current_time:
        raise ValueError("command has expired")
    if command["nonce"] in (seen_nonces or ()):
        raise ValueError("command nonce has already been used")

    if command["action"] in RUN_ACTIONS:
        if current_fencing_token is None:
            raise ValueError("authoritative fencing token is required")
        if command["fencing_token"] != current_fencing_token:
            raise ValueError("command fencing token is stale or superseded")
