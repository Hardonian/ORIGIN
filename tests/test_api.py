"""Tests for the research-lab API service: endpoints, security, auth, and worker management."""

from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from origin.experiments.api import make_handler
from origin.experiments.store import Store


@pytest.fixture
def test_server(tmp_path):
    store = Store(tmp_path / "runs")
    api_key = "test-secret-key-12345"
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store, api_key=api_key, auth_required=False))
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url, store, api_key
    server.shutdown()


def test_api_health_and_capabilities(test_server):
    base_url, store, _ = test_server

    # /api/health
    with urlopen(f"{base_url}/api/health") as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert data["status"] == "ok"
        assert "version" in data

    # /api/capabilities
    with urlopen(f"{base_url}/api/capabilities") as res:
        assert res.status == 200
        caps = json.loads(res.read().decode())
        assert caps["status"] == "ready"
        assert "simulators" in caps
        assert "gridworld" in caps["simulators"]
        assert "cpus" in caps
        assert caps["auth_enabled"] is True


def test_api_cors_preflight(test_server):
    base_url, _, _ = test_server
    req = Request(f"{base_url}/api/experiments", method="OPTIONS")
    with urlopen(req) as res:
        assert res.status == 204
        assert res.headers.get("Access-Control-Allow-Origin") == "*"
        assert "POST" in res.headers.get("Access-Control-Allow-Methods", "")


def test_api_post_requires_auth(test_server):
    base_url, _, api_key = test_server

    # Without token -> 401
    req = Request(f"{base_url}/api/workers/reap", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req)
    assert exc_info.value.code == 401

    # With invalid token -> 401
    req = Request(
        f"{base_url}/api/workers/reap",
        data=b"{}",
        headers={"Content-Type": "application/json", "Authorization": "Bearer wrong-token"},
        method="POST",
    )
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req)
    assert exc_info.value.code == 401

    # With valid Bearer token -> 200
    req = Request(
        f"{base_url}/api/workers/reap",
        data=b"{}",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert data["reaped"] is True


def test_api_workers_and_reap(test_server):
    base_url, store, api_key = test_server

    # Register mock worker
    store.register_worker("worker-1", "host-a", 1001)

    # Read workers
    with urlopen(f"{base_url}/api/workers") as res:
        assert res.status == 200
        rep = json.loads(res.read().decode())
        assert "workers" in rep
        assert len(rep["workers"]) == 1
        assert rep["workers"][0]["id"] == "worker-1"

    # Reap workers
    req = Request(
        f"{base_url}/api/workers/reap",
        data=json.dumps({"stale_after": 0.0}).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    with urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert data["reaped"] is True
        assert "worker-1" in data["dead_workers"]
