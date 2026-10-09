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


def test_api_security_headers(test_server):
    base_url, _, _ = test_server
    with urlopen(f"{base_url}/api/health") as res:
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "no-store" in res.headers.get("Cache-Control", "")


def test_api_logs_endpoint(test_server):
    base_url, store, _ = test_server
    log_file = store.root / "launched.log"
    log_file.write_text("line 1\nline 2\nline 3\n")

    with urlopen(f"{base_url}/api/logs?file=launched.log&lines=2") as res:
        assert res.status == 200
        data = json.loads(res.read().decode())
        assert data["file"] == "launched.log"
        assert data["lines"] == ["line 2", "line 3"]
        assert data["total_lines"] == 3

    # Traversal attempt rejected
    with pytest.raises(HTTPError) as exc_info:
        urlopen(f"{base_url}/api/logs?file=../etc/passwd")
    assert exc_info.value.code == 400


def test_api_export_trials(test_server):
    base_url, store, _ = test_server
    store.upsert_experiment("exp-1", "exp-name", "gridworld", "hash1", {}, "abc1234")
    store.add_trial("t-1", "exp-1", "random", 42, 1000)
    store.complete_trial("t-1", 100, 1.5, 1.2, {"reward": 1.5})

    # CSV export
    with urlopen(f"{base_url}/api/export?experiment=exp-1&format=csv") as res:
        assert res.status == 200
        assert "text/csv" in res.headers.get("Content-Type", "")
        body = res.read().decode()
        assert "id,experiment_id,algorithm,seed,status" in body
        assert "t-1,exp-1,random,42,done" in body

    # JSON export
    with urlopen(f"{base_url}/api/export?experiment=exp-1&format=json") as res:
        assert res.status == 200
        assert "application/json" in res.headers.get("Content-Type", "")
        data = json.loads(res.read().decode())
        assert len(data) == 1
        assert data[0]["id"] == "t-1"


def test_api_rate_limiter_logic():
    from origin.experiments.api import RateLimiter

    limiter = RateLimiter(max_requests=2, window_seconds=10.0)
    assert limiter.is_allowed("1.2.3.4") is True
    assert limiter.is_allowed("1.2.3.4") is True
    assert limiter.is_allowed("1.2.3.4") is False
    assert limiter.is_allowed("5.6.7.8") is True
