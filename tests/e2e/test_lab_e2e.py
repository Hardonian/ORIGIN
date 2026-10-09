"""End-to-end browser test for the ORIGIN research-lab UI.

Verifies the UI *renders live backend data* in a real headless Chromium — the one
item the earlier verification could not cover, because the cloud browser tool
refuses loopback addresses.

Navigation uses ``domcontentloaded`` (not ``networkidle``, which hangs whenever a
request stays in flight) and then waits on explicit DOM text, so the assertions
never depend on a quiet network. Console errors and failed requests are captured
and printed, so CI self-diagnoses instead of just timing out.

The suite is skipped unless ``ORIGIN_E2E=1`` is set. Run it via
``scripts/e2e_lab.sh``, which starts the API and the production UI server and
tears them down afterwards.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("ORIGIN_E2E") != "1",
    reason="set ORIGIN_E2E=1 (see scripts/e2e_lab.sh) to run browser E2E tests",
)

UI = os.environ.get("ORIGIN_UI_URL", "http://127.0.0.1:4317")
API = os.environ.get("ORIGIN_API_URL", "http://127.0.0.1:8788")
WAIT_MS = int(os.environ.get("ORIGIN_E2E_TIMEOUT_MS", "60000"))


def _api(path: str) -> Any:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as r:
        return json.loads(r.read())


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        yield b
        b.close()


@pytest.fixture()
def page(browser):
    p = browser.new_page()
    diagnostics: list[str] = []
    p.on("console", lambda m: diagnostics.append(f"console.{m.type}: {m.text}"))
    p.on("pageerror", lambda e: diagnostics.append(f"pageerror: {e}"))
    p.on("requestfailed", lambda r: diagnostics.append(f"requestfailed: {r.url} :: {r.failure}"))
    yield p
    if diagnostics:
        print("\n--- browser diagnostics ---")
        for line in diagnostics[-25:]:
            print("  " + line)
    p.close()


def _goto(page, path: str) -> None:
    """Navigate and confirm the HTML actually loaded (independent of network idleness).

    A freshly started ``next start`` can refuse the very first request to a
    not-yet-warmed route, so a single short retry is allowed — the assertion
    (HTTP 200) is unchanged and still enforced on the retry.
    """
    last = None
    for _ in range(3):
        resp = page.goto(f"{UI}{path}", wait_until="domcontentloaded", timeout=WAIT_MS)
        assert resp is not None, f"no response for {path}"
        if resp.ok:
            assert page.title(), "page has no title; document did not render"
            return
        last = resp.status
        page.wait_for_timeout(2000)
    raise AssertionError(f"HTTP {last} for {path} after 3 attempts")


def _wait_for_text(page, needle: str) -> str:
    page.wait_for_function(
        "t => document.body && document.body.innerText.includes(t)",
        arg=needle,
        timeout=WAIT_MS,
    )
    return page.inner_text("body")


def _select_experiment(page, experiment_id: str) -> None:
    """Wait for the asynchronously loaded experiment selector before using it."""
    page.wait_for_function(
        "id => [...document.querySelector('select')?.options ?? []].some(o => o.value === id)",
        arg=experiment_id,
        timeout=WAIT_MS,
    )
    page.locator("select").first.select_option(experiment_id)


# --------------------------------------------------------------------------- #
def test_overview_renders_live_experiment(page):
    """The overview must show the persisted experiment and its method comparison."""
    exps = _api("/api/experiments")
    assert exps, "no experiments in store; run an experiment first"
    exp_id = exps[0]["id"]

    _goto(page, "/")
    body = _wait_for_text(page, exp_id)

    assert "Research overview" in body
    cmp = _api(f"/api/compare?experiment={exp_id}")
    for algo in cmp["comparison"]:
        assert algo in body, f"method {algo} missing from the comparison table"


def _grid_experiment_with_trained_trial() -> tuple[str, dict[str, Any]] | None:
    """Pick a grid-world experiment with a trained trial."""
    for e in _api("/api/experiments"):
        detail = _api(f"/api/experiments/{e['id']}")
        cfg = json.loads(detail["experiment"]["config_json"])
        if cfg.get("env_kind", "gridworld") != "gridworld":
            continue
        trained = [
            t for t in detail["trials"]
            if t["status"] == "done" and t["algorithm"] not in ("random", "heuristic")
        ]
        if trained:
            return e["id"], trained[0]
    return None


def _embodied_experiment_with_trial() -> tuple[str, dict[str, Any]] | None:
    """Pick any finished embodied trial; a static body plan needs no checkpoint."""
    for e in _api("/api/experiments"):
        detail = _api(f"/api/experiments/{e['id']}")
        cfg = json.loads(detail["experiment"]["config_json"])
        if cfg.get("env_kind", "gridworld") != "embodied":
            continue
        trial = next((t for t in detail["trials"] if t["status"] == "done"), None)
        if trial:
            return e["id"], trial
    return None


def test_world_viewer_renders_grid_and_trajectory(page):
    """The world viewer must render a real grid with a trained organism's trajectory."""
    found = _grid_experiment_with_trained_trial()
    if found is None:
        pytest.skip("no gridworld experiment with a trained trial in the store (viewer is grid-only)")
    exp_id, trial = found

    _goto(page, "/world")
    _wait_for_text(page, "World viewer")
    # The page defaults to the newest experiment, which may be one the grid-only
    # viewer cannot render; drive the selector to a grid experiment explicitly.
    _select_experiment(page, exp_id)
    page.wait_for_selector("div.cell", timeout=WAIT_MS)
    cells = page.locator("div.cell").count()

    world = _api(f"/api/world?experiment={exp_id}&trial={trial['id']}&seed=101")
    expected = len(world["grid"]) * len(world["grid"][0])
    assert cells == expected, f"rendered {cells} cells, backend grid has {expected}"

    body = page.inner_text("body")
    assert "step 0" in body
    assert "empty" in body and "obstacle" in body and "agent" in body  # legend

    page.locator("button:has-text('▶')").first.click()
    _wait_for_text(page, "step 1")


def test_world_viewer_inspects_embodied_body_plan(page):
    """Embodied studies expose their declared body, never a fake motion replay."""
    found = _embodied_experiment_with_trial()
    if found is None:
        pytest.skip("no completed embodied experiment in the store")
    exp_id, trial = found

    plan = _api(f"/api/morphology?experiment={exp_id}&trial={trial['id']}")
    _goto(page, "/world")
    _select_experiment(page, exp_id)
    body = _wait_for_text(page, "schematic, not a physics replay")

    assert "Calibration gate" in body
    assert "Latest captured evidence" in body
    assert "low longitudinal grip" in body
    assert plan["body"]["joint_axis"] in body


def test_benchmark_renders_transfer_matrix(page):
    exps = _api("/api/experiments")
    exp_id = exps[0]["id"]
    cmp = _api(f"/api/compare?experiment={exp_id}")
    variants = {v for c in cmp["comparison"].values() for v in c["transfer"]}
    assert variants, "no transfer variants recorded"

    _goto(page, "/benchmark")
    # wait for data-derived content, not the static heading: the page renders
    # an empty state before its fetch resolves.
    body = _wait_for_text(page, sorted(variants)[0])
    assert "Held-out performance" in body
    assert "Transfer" in body
    for v in sorted(variants):
        assert v in body, f"transfer variant {v} missing from the matrix"


def test_failure_inspector_reports_state(page):
    failures = _api("/api/failures")
    _goto(page, "/failures")
    if failures:
        body = _wait_for_text(page, failures[0]["algorithm"])
        assert failures[0]["id"] in body or failures[0]["algorithm"] in body
    else:
        # the empty state only appears once the fetch has resolved
        body = _wait_for_text(page, "No failed trials")
    assert "Failure inspector" in body


def test_artifacts_page_lists_generated_files(page):
    exps = _api("/api/experiments")
    exp_id = exps[0]["id"]
    arts = _api(f"/api/artifacts?experiment={exp_id}")
    assert arts, "no artifacts registered"

    _goto(page, "/artifacts")
    # wait for a real artifact row to render, not the static heading
    body = _wait_for_text(page, arts[0]["kind"])
    assert "Research artifacts" in body
    for k in {a["kind"] for a in arts}:
        assert k in body, f"artifact kind {k} missing"
    assert "No artifacts registered yet." not in body


def test_designer_loads_validated_protocols(page):
    _goto(page, "/designer")
    protocols = _api("/api/protocols")
    assert protocols, "no protocols exposed"
    body = _wait_for_text(page, protocols[0]["name"])
    assert "Experiment designer" in body
    assert page.locator("textarea").input_value().strip().startswith("{")


def test_evolution_page_renders_distribution(page):
    exps = _api("/api/experiments")
    assert exps, "no experiments in store"
    exp_id = exps[0]["id"]

    _goto(page, "/evolution")
    body = _wait_for_text(page, "Evolution explorer")
    assert "Fitness distributions" in body
    _select_experiment(page, exp_id)
    body = page.inner_text("body")
    assert "seed" in body or "mean best fitness" in body or "No trials" in body


def test_workers_dashboard_renders_cluster_status(page):
    _goto(page, "/workers")
    body = _wait_for_text(page, "System Capabilities")
    assert "Cluster & Compute Workers" in body
    assert "Reap Stale Workers" in body
