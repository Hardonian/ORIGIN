"""Cross-platform Python runner for the ORIGIN Lab E2E browser tests.

Starts the origin-api backend and the production Next.js Lab UI, preflights all
routes, executes playwright tests under pytest with ORIGIN_E2E=1, and always cleans
up background processes.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def find_free_port(preferred: int, host: str = "127.0.0.1") -> int:
    if is_port_free(preferred, host):
        return preferred
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind((host, 0))
    port = int(probe.getsockname()[1])
    probe.close()
    return port


def wait_for_url(url: str, name: str, timeout_sec: int = 45) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status < 400:
                    return True
        except Exception:
            time.sleep(1)
    print(f"ERROR: {name} did not become available at {url} within {timeout_sec}s", file=sys.stderr)
    return False


def terminate_proc(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if sys.platform == "win32":
        with contextlib.suppress(Exception):
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            with contextlib.suppress(Exception):
                proc.kill()


def kill_process_on_port(port: int) -> None:
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True)
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid != "0":
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Lab UI End-to-End tests")
    parser.add_argument("--api-port", type=int, default=8788)
    parser.add_argument("--ui-port", type=int, default=4317)
    parser.add_argument("--store", default="runs")
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="reuse an existing build only when it was compiled for the selected API URL",
    )
    parser.add_argument("--seed", action="store_true", help="force run smoke experiment before testing")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    # 1. Ensure test experiment is present in store
    store_dir = repo_root / args.store
    db_file = store_dir / "origin.db"
    if args.seed or not db_file.exists():
        print("[e2e] Seeding deterministic smoke experiment...")
        res = subprocess.run(
            [sys.executable, "-m", "origin.experiments.runner", "--config", "configs/smoke.json", "--store", str(store_dir), "--jobs", "2"],
            cwd=str(repo_root),
        )
        if res.returncode != 0:
            print("[e2e] Failed to seed experiment", file=sys.stderr)
            return res.returncode

    api_port = find_free_port(args.api_port)
    ui_port = find_free_port(args.ui_port)
    if api_port != args.api_port:
        print(f"[e2e] Port {args.api_port} busy -> API using {api_port}")
    if ui_port != args.ui_port:
        print(f"[e2e] Port {args.ui_port} busy -> UI using {ui_port}")

    # Ensure ports are clean
    kill_process_on_port(api_port)
    kill_process_on_port(ui_port)

    # 2. Build UI if needed
    lab_dir = repo_root / "apps" / "lab"
    next_dist = lab_dir / ".next"
    api_url = f"http://127.0.0.1:{api_port}"
    api_marker = next_dist / "origin-api-url.txt"
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    build_env = os.environ.copy()
    # NEXT_PUBLIC variables are compiled into Next static output.  Passing this
    # only to `next start` makes a dynamically selected API port look healthy
    # while the browser continues calling the old port from a previous build.
    build_env["NEXT_PUBLIC_ORIGIN_API"] = api_url
    cached_api_url = api_marker.read_text(encoding="utf-8").strip() if api_marker.exists() else ""
    reuse_build = args.skip_build and next_dist.exists() and cached_api_url == api_url
    if not reuse_build:
        print("[e2e] Building Lab UI production bundle...")
        b_res = subprocess.run([npm_cmd, "run", "build"], cwd=str(lab_dir), env=build_env)
        if b_res.returncode != 0:
            print("[e2e] UI build failed", file=sys.stderr)
            return b_res.returncode
        api_marker.write_text(api_url + "\n", encoding="utf-8")
    elif args.skip_build:
        print(f"[e2e] Reusing UI build compiled for {api_url}")

    api_proc: subprocess.Popen | None = None
    ui_proc: subprocess.Popen | None = None

    try:
        # 3. Start API server
        print(f"[e2e] Starting API server on http://127.0.0.1:{api_port}...")
        api_proc = subprocess.Popen(
            [sys.executable, "-m", "origin.experiments.api", "--store", str(store_dir), "--host", "127.0.0.1", "--port", str(api_port)],
            cwd=str(repo_root),
        )
        if not wait_for_url(f"http://127.0.0.1:{api_port}/api/health", "API"):
            return 1

        print("[e2e] Checking the live UI↔API contract...")
        smoke_env = os.environ.copy()
        smoke_env["ORIGIN_API"] = api_url
        smoke = subprocess.run(
            ["node", str(lab_dir / "scripts" / "smoke-api.mjs")],
            cwd=str(repo_root),
            env=smoke_env,
        )
        if smoke.returncode != 0:
            print("[e2e] API contract smoke test failed", file=sys.stderr)
            return smoke.returncode

        # 4. Start Next.js Lab server
        print(f"[e2e] Starting Lab UI server on http://127.0.0.1:{ui_port}...")
        env = build_env
        ui_proc = subprocess.Popen(
            [npx_cmd, "next", "start", "-p", str(ui_port), "-H", "127.0.0.1"],
            cwd=str(lab_dir),
            env=env,
        )
        if not wait_for_url(f"http://127.0.0.1:{ui_port}/", "Lab UI"):
            return 1

        # 5. Route preflight
        print("[e2e] Preflighting routes...")
        routes = ["/", "/world", "/evolution", "/designer", "/benchmark", "/workers", "/artifacts", "/failures"]
        for r in routes:
            url = f"http://127.0.0.1:{ui_port}{r}"
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    print(f"  {r:<14} HTTP {resp.status}")
            except urllib.error.HTTPError as e:
                print(f"  {r:<14} HTTP {e.code}")
            except Exception as e:
                print(f"  {r:<14} ERROR: {e}")

        # 6. Run browser tests
        print("[e2e] Running Playwright browser test suite...")
        test_env = os.environ.copy()
        test_env["ORIGIN_E2E"] = "1"
        test_env["ORIGIN_UI_URL"] = f"http://127.0.0.1:{ui_port}"
        test_env["ORIGIN_API_URL"] = f"http://127.0.0.1:{api_port}"

        cmd = [sys.executable, "-m", "pytest", "tests/e2e", "-v", "-p", "no:cacheprovider"]
        res = subprocess.run(cmd, cwd=str(repo_root), env=test_env)
        return res.returncode

    finally:
        print("[e2e] Tearing down servers...")
        terminate_proc(ui_proc)
        terminate_proc(api_proc)
        kill_process_on_port(ui_port)
        kill_process_on_port(api_port)
        print("[e2e] Done.")


if __name__ == "__main__":
    sys.exit(main())
