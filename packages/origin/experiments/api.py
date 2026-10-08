"""Read + bounded-launch API over the experiment store (loopback by default).

A dependency-free ``http.server`` service so the research-lab UI (and humans)
can inspect persisted experiments and launch *bounded* new ones without a cloud
database or extra services. Binds to loopback only by default.
"""

from __future__ import annotations

import argparse
import json
import statistics as st
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from origin.experiments.store import Store

MAX_LAUNCH_BUDGET = 5_000_000  # hard cap for UI-launched experiments


def _compare(store: Store, exp_id: str) -> dict:
    trials = [t for t in store.trials(exp_id) if t["status"] == "done"]
    by_algo: dict[str, list[dict]] = {}
    for t in trials:
        by_algo.setdefault(t["algorithm"], []).append(t)

    comparison: dict[str, dict] = {}
    for algo, ts in by_algo.items():
        test, train, interactions = [], [], []
        for t in ts:
            m = json.loads(t["metrics_json"]) if t.get("metrics_json") else {}
            if m.get("test_mean_reward") is not None:
                test.append(m["test_mean_reward"])
            if t.get("train_fitness") is not None:
                train.append(t["train_fitness"])
            interactions.append(t["interactions"] or 0)

        transfer_agg: dict[str, dict[str, list[float]]] = {}
        for t in ts:
            tr = json.loads(t["transfer_json"]) if t.get("transfer_json") else {}
            for name, entry in (tr or {}).items():
                if "zero_shot_mean_reward" in entry:
                    transfer_agg.setdefault(name, {"zero_shot": [], "adapted": [], "kind": entry.get("kind", "")})
                    transfer_agg[name]["zero_shot"].append(entry["zero_shot_mean_reward"])
                    if "adapted_mean_reward" in entry:
                        transfer_agg[name]["adapted"].append(entry["adapted_mean_reward"])

        comparison[algo] = {
            "n": len(ts),
            "test_mean_reward": round(st.mean(test), 4) if test else None,
            "test_std_reward": round(st.pstdev(test), 4) if len(test) > 1 else 0.0,
            "train_mean_fitness": round(st.mean(train), 4) if train else None,
            "mean_interactions": round(st.mean(interactions), 1) if interactions else 0,
            "transfer": {
                name: {
                    "kind": v["kind"],
                    "zero_shot": round(st.mean(v["zero_shot"]), 3),
                    "adapted": round(st.mean(v["adapted"]), 3) if v["adapted"] else None,
                    "adaptation_gain": (round(st.mean(v["adapted"]) - st.mean(v["zero_shot"]), 3) if v["adapted"] else None),
                }
                for name, v in transfer_agg.items()
            },
        }
    return {"experiment_id": exp_id, "n_done": len(trials), "comparison": comparison}


def _world(store: Store, exp_id: str, trial_id: str, seed: int) -> dict:
    """Replay a stored organism in a freshly generated world (real backend state)."""
    from origin.organisms.organism import Organism

    exp = store.experiment(exp_id)
    if not exp:
        raise FileNotFoundError(f"experiment {exp_id} not found")
    cfg = json.loads(exp["config_json"])
    env_cfg = cfg["env"]

    org_path = Path(store.root) / exp_id / f"{trial_id}.organism.json"
    if not org_path.exists():
        raise FileNotFoundError(f"organism for trial {trial_id} not found (untrained baseline trials have none)")
    org = Organism.from_dict(json.loads(org_path.read_text()))

    env = org.make_env(__import__("origin.environments.gridworld", fromlist=["GridWorldConfig"]).GridWorldConfig.from_dict(env_cfg), seed=seed)
    env_cfg_resolved = env.config.to_dict()
    obs, _ = env.reset(seed=seed)
    trajectory = []
    grid = env._grid.tolist()
    reward = 0.0
    done = False
    for _ in range(env_cfg_resolved["max_steps"]):
        a = org.act(obs)
        obs, r, term, trunc, info = env.step(a)
        reward += r
        trajectory.append({"agent": info["agent"], "action": a, "reward": round(r, 4), "collected": info["collected"], "energy": round(info["energy"], 2)})
        done = term or trunc
        if done:
            break
    return {
        "experiment_id": exp_id,
        "trial_id": trial_id,
        "seed": seed,
        "config": env_cfg_resolved,
        "grid": grid,
        "trajectory": trajectory,
        "total_reward": round(reward, 4),
        "steps": len(trajectory),
        "terminated": bool(done),
        "morphology": org.morph.to_dict(),
    }


def _list_protocols() -> list[dict]:
    out = []
    cfg_dir = Path(__file__).resolve().parents[3] / "configs"
    if not cfg_dir.exists():
        cfg_dir = Path("configs")
    for p in sorted(cfg_dir.glob("*.json")):
        try:
            cfg = json.loads(p.read_text())
            out.append({"file": p.name, "name": cfg.get("name"), "protocol": cfg.get("protocol"), "budget": cfg.get("budget"), "description": cfg.get("description", ""), "config": cfg})
        except Exception:
            continue
    return out


def _launch(store: Store, cfg: dict) -> dict:
    from origin.experiments.runner import validate_config

    validate_config(cfg)
    if int(cfg["budget"]) > MAX_LAUNCH_BUDGET:
        raise ValueError(f"budget exceeds the UI launch cap ({MAX_LAUNCH_BUDGET})")
    tmp = Path(store.root) / f"launched-{abs(hash(json.dumps(cfg, sort_keys=True))) % 10**8}.json"
    tmp.write_text(json.dumps(cfg, indent=2))
    log = Path(store.root) / "launched.log"
    with log.open("a") as fh:
        subprocess.Popen(  # noqa: S603 - args list, no shell; cfg already validated
            [sys.executable, "-m", "origin.experiments.runner", "--config", str(tmp), "--store", str(store.root), "--jobs", "2"],
            stdout=fh, stderr=subprocess.STDOUT, cwd=str(Path(store.root).resolve()),
        )
    return {"launched": True, "config": str(tmp), "log": str(log)}


def make_handler(store: Store) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "OriginLab/1.0"

        def _send(self, payload, code: int = 200) -> None:
            body = json.dumps(payload, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # quieter
            pass

        def _serve_artifact(self, q) -> None:
            """Serve a registered artifact file, confined to the store root."""
            try:
                aid = int(q.get("id", ["-1"])[0])
            except ValueError:
                return self._send({"error": "invalid id"}, 400)
            rows = store.artifacts()
            row = next((r for r in rows if r["id"] == aid), None)
            if not row:
                return self._send({"error": "artifact not found"}, 404)
            root = Path(store.root).resolve()
            p = Path(row["path"]).resolve()
            if root not in p.parents and p != root:
                return self._send({"error": "path outside store"}, 403)
            if not p.exists():
                return self._send({"error": "file missing"}, 404)
            data = p.read_bytes()
            ctype = "image/png" if p.suffix == ".png" else ("text/csv" if p.suffix == ".csv" else "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            url = urlparse(self.path)
            q = parse_qs(url.query)
            try:
                if url.path == "/api/health":
                    return self._send({"status": "ok", "store": str(store.root), "version": "0.1.0"})
                if url.path == "/api/artifact-file":
                    return self._serve_artifact(q)
                if url.path == "/api/experiments":
                    exps = store.list_experiments()
                    for e in exps:
                        e["summary"] = store.summary(e["id"])
                    return self._send(exps)
                if url.path == "/api/protocols":
                    return self._send(_list_protocols())
                if url.path.startswith("/api/experiments/"):
                    exp_id = url.path.rsplit("/", 1)[-1]
                    exp = store.experiment(exp_id)
                    if not exp:
                        return self._send({"error": "not found"}, 404)
                    return self._send({"experiment": exp, "trials": store.trials(exp_id), "summary": store.summary(exp_id), "artifacts": store.artifacts(exp_id)})
                if url.path == "/api/trials":
                    return self._send(store.trials(q.get("experiment", [None])[0]))
                if url.path == "/api/compare":
                    exp_id = q.get("experiment", [None])[0] or ""
                    if not exp_id:
                        return self._send({"error": "experiment query param required"}, 400)
                    return self._send(_compare(store, exp_id))
                if url.path == "/api/artifacts":
                    return self._send(store.artifacts(q.get("experiment", [None])[0]))
                if url.path == "/api/failures":
                    return self._send([t for t in store.trials() if t["status"] == "failed"])
                if url.path == "/api/world":
                    exp_id = q.get("experiment", [None])[0] or ""
                    trial_id = q.get("trial", [None])[0] or ""
                    seed = int(q.get("seed", ["0"])[0])
                    if not exp_id or not trial_id:
                        return self._send({"error": "experiment and trial required"}, 400)
                    return self._send(_world(store, exp_id, trial_id, seed))
                return self._send({"error": "unknown endpoint", "path": url.path}, 404)
            except FileNotFoundError as exc:
                return self._send({"error": str(exc)}, 404)
            except Exception as exc:  # pragma: no cover
                return self._send({"error": f"{type(exc).__name__}: {exc}"}, 500)

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if url.path != "/api/experiments":
                return self._send({"error": "unknown endpoint"}, 404)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 1_000_000:
                    return self._send({"error": "invalid body size"}, 400)
                cfg = json.loads(self.rfile.read(length))
                return self._send(_launch(store, cfg))
            except ValueError as exc:
                return self._send({"error": str(exc)}, 400)
            except Exception as exc:  # pragma: no cover
                return self._send({"error": f"{type(exc).__name__}: {exc}"}, 500)

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ORIGIN research-lab API")
    ap.add_argument("--store", default="runs")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8788)
    args = ap.parse_args(argv)
    store = Store(args.store)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(store))
    print(f"ORIGIN lab API on http://{args.host}:{args.port} (store={Path(args.store).resolve()})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
