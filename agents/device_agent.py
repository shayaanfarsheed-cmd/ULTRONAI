#!/usr/bin/env python3
"""ULTRON device heartbeat agent. Pairing only; it does not execute jobs or commands."""

from __future__ import annotations

import getpass
import json
import os
import platform
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

AGENT_VERSION = "0.1.0"
HEARTBEAT_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 15


class AgentError(RuntimeError):
    pass


def platform_name() -> str:
    value = platform.system().lower()
    return {"windows": "windows", "darwin": "macos", "linux": "linux"}.get(value, "other")


def request_json(base_url: str, publishable_key: str, route: str,
                 method: str = "GET", payload: dict | None = None,
                 bearer_token: str | None = None) -> dict:
    url = base_url.rstrip("/") + "/functions/v1/device-control/" + route.lstrip("/")
    headers = {
        "apikey": publishable_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
    }
    if bearer_token:
        headers["Authorization"] = "Bearer " + bearer_token
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read(16384)
            if len(raw) >= 16384:
                raise AgentError("The pairing service returned an oversized response.")
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise AgentError("The pairing service returned an invalid response.")
            return data
    except urllib.error.HTTPError as error:
        # Never include request headers, request bodies, or bearer tokens in errors.
        try:
            data = json.loads(error.read(4096).decode("utf-8"))
            message = data.get("error", "request rejected") if isinstance(data, dict) else "request rejected"
        except Exception:
            message = "request rejected"
        raise AgentError(f"Pairing service returned HTTP {error.code}: {message}") from None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise AgentError("Could not reach the ULTRON pairing service.") from None


def pair_device(base_url: str, publishable_key: str) -> tuple[str, str]:
    print("Enter the Challenge ID shown in the ULTRON owner dashboard.")
    challenge_id = input("Challenge ID: ").strip()
    code = getpass.getpass("Eight-digit pairing code: ").strip()
    if len(challenge_id) != 36 or not code.isdigit() or len(code) != 8:
        raise AgentError("Challenge ID or pairing code format is invalid.")

    name = input("Device name [" + platform.node()[:80] + "]: ").strip() or platform.node()
    name = name[:80]
    payload = {
        "challenge_id": challenge_id,
        "code": code,
        "device_name": name,
        "platform": platform_name(),
        "capabilities": {
            "agent_version": AGENT_VERSION,
            "python_version": platform.python_version(),
            "platform": platform_name(),
        },
    }
    data = request_json(base_url, publishable_key, "redeem", "POST", payload)
    token = data.get("device_token")
    device_id = data.get("device_id")
    if not isinstance(token, str) or len(token) != 64 or not isinstance(device_id, str):
        raise AgentError("The pairing service returned incomplete device credentials.")
    print("Device paired. Device ID: " + device_id)
    print("The credential is held in memory only; it is never written to disk or printed.")
    return device_id, token


def heartbeat_loop(base_url: str, publishable_key: str, token: str) -> None:
    print("ULTRON agent is online. Heartbeat interval: 60 seconds. No remote commands are accepted.")
    while True:
        try:
            data = request_json(
                base_url, publishable_key, "heartbeat", "POST",
                {"capabilities": {
                    "agent_version": AGENT_VERSION,
                    "python_version": platform.python_version(),
                    "platform": platform_name(),
                }},
                bearer_token=token,
            )
            if data.get("accepted") is not True:
                raise AgentError("The pairing service did not accept the heartbeat.")
            print("Heartbeat accepted.")
            time.sleep(HEARTBEAT_SECONDS)
        except AgentError as error:
            print(str(error), file=sys.stderr)
            if "HTTP 401" in str(error):
                print("Device credential is revoked or invalid. Stop and pair again.", file=sys.stderr)
                return
            time.sleep(HEARTBEAT_SECONDS)


def main() -> int:
    base_url = os.environ.get("ULTRON_SUPABASE_URL", "").strip()
    publishable_key = os.environ.get("ULTRON_PUBLISHABLE_KEY", "").strip()
    if not base_url or not publishable_key:
        print("Set ULTRON_SUPABASE_URL and ULTRON_PUBLISHABLE_KEY first.", file=sys.stderr)
        return 2
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1"):
        print("The Supabase URL must use HTTPS.", file=sys.stderr)
        return 2
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        print("ULTRON_SUPABASE_URL is invalid.", file=sys.stderr)
        return 2

    try:
        if "--pair" in sys.argv[1:]:
            _, token = pair_device(base_url, publishable_key)
        else:
            token = os.environ.get("ULTRON_DEVICE_TOKEN", "").strip()
            if len(token) != 64:
                print("Use --pair or provide ULTRON_DEVICE_TOKEN through the server's secret manager.", file=sys.stderr)
                return 2
        heartbeat_loop(base_url, publishable_key, token)
        return 0
    except (AgentError, KeyboardInterrupt) as error:
        if isinstance(error, KeyboardInterrupt):
            print("\nULTRON agent stopped.")
            return 130
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
