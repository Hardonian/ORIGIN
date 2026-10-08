"""ORIGIN Doctor: Environment, dependency, store, and network diagnostic CLI.

Run `origin-doctor` to verify your environment, dependencies, store consistency,
and compute distribution readiness.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


def check_core_dependencies() -> list[tuple[str, bool, str]]:
    deps = [
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("pandas", "pandas"),
        ("pyarrow", "pyarrow"),
        ("gymnasium", "gymnasium"),
        ("matplotlib", "matplotlib"),
        ("yaml", "PyYAML"),
        ("filelock", "filelock"),
    ]
    results = []
    for mod_name, pkg_name in deps:
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, "__version__", "installed")
            results.append((pkg_name, True, ver))
        except ImportError as exc:
            results.append((pkg_name, False, str(exc)))
    return results


def check_optional_extensions() -> list[tuple[str, bool, str]]:
    extensions = [
        ("pybullet", "pybullet (Embodied articulated physics)", "PyBullet DIRECT engine"),
        ("torch", "PyTorch (Deep RL accelerator)", "CUDA/CPU tensor computing"),
        ("stable_baselines3", "Stable-Baselines3 (PPO/SAC)", "RL baseline algorithms"),
        ("playwright", "Playwright (Browser E2E testing)", "Headless UI testing"),
    ]
    results = []
    for mod_name, label, purpose in extensions:
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, "__version__", "installed")
            results.append((label, True, f"v{ver} ({purpose})"))
        except ImportError:
            results.append((label, False, f"optional, not installed ({purpose})"))
    return results


def check_store(store_path: str | Path) -> dict[str, Any]:
    path = Path(store_path)
    if not path.exists():
        return {"exists": False, "status": f"Directory not found: {path}"}

    db_path = path / "origin.db"
    if not db_path.exists():
        return {"exists": True, "initialized": False, "status": "Empty store (no origin.db)"}

    try:
        from origin.experiments.store import Store

        store = Store(path)
        exps = store.list_experiments()
        counts = store.trial_counts()
        workers = store.workers()
        now = time.time()
        active_workers = [w for w in workers if w["status"] == "running" and (now - float(w["last_heartbeat"])) <= 120]
        stale_workers = [w for w in workers if w["status"] == "running" and (now - float(w["last_heartbeat"])) > 120]
        return {
            "exists": True,
            "initialized": True,
            "experiments": len(exps),
            "trial_counts": counts,
            "active_workers": len(active_workers),
            "stale_workers": len(stale_workers),
            "total_workers": len(workers),
        }
    except Exception as exc:
        return {"exists": True, "error": str(exc)}


def check_api_server(host: str = "127.0.0.1", port: int = 8788) -> dict[str, Any]:
    url = f"http://{host}:{port}/api/capabilities"
    try:
        with urlopen(url, timeout=1.5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode())
                return {"reachable": True, "details": data}
            return {"reachable": True, "status_code": res.status}
    except URLError:
        return {"reachable": False, "status": f"No service running on {host}:{port}"}
    except Exception as exc:
        return {"reachable": False, "status": str(exc)}


def check_lab_ui(repo_root: Path) -> dict[str, Any]:
    lab_dir = repo_root / "apps" / "lab"
    node_bin = shutil.which("node")
    npm_bin = shutil.which("npm")
    node_modules = lab_dir / "node_modules"
    next_dist = lab_dir / ".next"

    node_ver = "missing"
    if node_bin:
        try:
            node_ver = subprocess.check_output([node_bin, "--version"], text=True).strip()
        except Exception:
            node_ver = "error"

    return {
        "lab_dir_exists": lab_dir.exists(),
        "node_installed": bool(node_bin),
        "node_version": node_ver,
        "npm_installed": bool(npm_bin),
        "node_modules_present": node_modules.exists(),
        "build_present": next_dist.exists(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ORIGIN Doctor: Environment diagnostics and verification")
    ap.add_argument("--store", default="runs", help="path to experiment store")
    ap.add_argument("--json", action="store_true", help="output structured JSON report")
    args = ap.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    core_deps = check_core_dependencies()
    opt_deps = check_optional_extensions()
    store_info = check_store(args.store)
    api_info = check_api_server()
    ui_info = check_lab_ui(repo_root)

    plat_info = {
        "os": platform.system(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "cpus": os.cpu_count() or 1,
    }

    report: dict[str, Any] = {
        "timestamp": time.time(),
        "platform": plat_info,
        "core_dependencies": [{"name": n, "ok": ok, "version": v} for n, ok, v in core_deps],
        "optional_extensions": [{"name": n, "ok": ok, "details": d} for n, ok, d in opt_deps],
        "store": store_info,
        "api_service": api_info,
        "lab_ui": ui_info,
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("==================================================================")
    print("                     ORIGIN SYSTEM DIAGNOSTICS                    ")
    print("==================================================================")
    print(f"Platform:      {plat_info['platform']} ({plat_info['cpus']} CPUs)")
    print(f"Python:        {plat_info['python']} ({plat_info['executable']})")
    print()

    print("--- Core Dependencies -----------------------------------------")
    all_core_ok = True
    for name, ok, ver in core_deps:
        icon = "[+]" if ok else "[-]"
        print(f"  {icon} {name:<18} : {ver}")
        if not ok:
            all_core_ok = False
    print()

    print("--- Optional Extensions ---------------------------------------")
    for name, ok, details in opt_deps:
        icon = "[+]" if ok else "[ ]"
        print(f"  {icon} {name:<42} : {details}")
    print()

    print("--- Experiment Store ------------------------------------------")
    if store_info.get("initialized"):
        print(f"  [+] Store Location  : {Path(args.store).resolve()}")
        print(f"  [+] Experiments     : {store_info['experiments']}")
        print(f"  [+] Trial Counts    : {store_info['trial_counts']}")
        print(f"  [+] Workers (active): {store_info['active_workers']} active / {store_info['stale_workers']} stale")
    elif store_info.get("exists"):
        print(f"  [ ] Store Location  : {Path(args.store).resolve()} (not initialized yet)")
    else:
        print(f"  [ ] Store Location  : {Path(args.store).resolve()} (directory created upon first run)")
    print()

    print("--- Research Lab UI & API -------------------------------------")
    if api_info["reachable"]:
        print("  [+] API Service     : Running on 127.0.0.1:8788")
        if "details" in api_info:
            print(f"      - Simulators    : {', '.join(api_info['details'].get('simulators', []))}")
            print(f"      - Auth Enabled  : {api_info['details'].get('auth_enabled')}")
    else:
        print(f"  [ ] API Service     : Not currently running ({api_info['status']})")

    if ui_info["node_installed"]:
        print(f"  [+] Node.js Runtime : {ui_info['node_version']}")
        print(f"  [+] Dependencies    : {'installed' if ui_info['node_modules_present'] else 'run npm install'}")
        print(f"  [+] Production Build: {'built' if ui_info['build_present'] else 'not built (run npm run build)'}")
    else:
        print("  [ ] Node.js Runtime : Not detected on PATH")
    print("==================================================================")

    return 0 if all_core_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
