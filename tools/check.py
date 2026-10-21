"""animkit required-check runner.

Runs the required test suites as subprocesses, captures their ACTUAL exit
codes (never a filter's), stores complete logs, and prints a short summary.
Exit code: 0 only if every required check passed.

Usage:
    python tools/check.py --fast    # layout + audio + no-local-paths
    python tools/check.py           # full: fast + cli + tex (tex auto-skips)
    python tools/check.py --list

The pre-commit hook runs --fast; the pre-push hook runs the full set.
A failing run blocks commit/push until the affected check passes.
Complete logs: logs/<run-id>/<check>.log   (gitignored)
Last-run status:  logs/last_run.json
"""

import argparse
import datetime
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SLOW_SUITES = {"test_cli.py", "test_tex.py"}   # excluded from the fast set


def discover() -> list[str]:
    """Every tests/test_*.py is a required check — discovered, not hardcoded,
    so a newly added failing test can never escape the gate."""
    return sorted(p.name for p in (REPO / "tests").glob("test_*.py"))


def run_check(test_file: str, log_dir: Path, timeout: int = 1800) -> dict:
    """Run one suite in a subprocess; capture the real exit code + full log."""
    log_path = log_dir / f"{test_file.replace('.py', '')}.log"
    proc = subprocess.run(
        [sys.executable, str(REPO / "tests" / test_file)],
        cwd=str(REPO), capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace",
    )
    log_path.write_text(
        f"command: {sys.executable} tests/{test_file}\n"
        f"exit_code: {proc.returncode}\n"
        f"{'-' * 60}\n{proc.stdout}\n{proc.stderr}", encoding="utf-8")
    passed = proc.returncode == 0
    tail = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()][-3:]
    return {"check": test_file, "passed": passed,
            "exit_code": proc.returncode, "log": str(log_path),
            "summary": tail[-1] if tail else ""}


def main() -> int:
    ap = argparse.ArgumentParser(description="animkit required-check runner")
    ap.add_argument("--fast", action="store_true",
                    help="fast set only (layout, audio, no-local-paths)")
    ap.add_argument("--list", action="store_true", help="list checks and exit")
    args = ap.parse_args()

    all_checks = discover()
    checks = [c for c in all_checks if c not in SLOW_SUITES] if args.fast else all_checks
    if args.list:
        print("\n".join(checks))
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = REPO / "logs" / stamp
    log_dir.mkdir(parents=True, exist_ok=True)

    print(f"[runner] {len(checks)} checks in parallel; logs: {log_dir}")
    with ThreadPoolExecutor(max_workers=len(checks)) as pool:
        futures = {pool.submit(run_check, check, log_dir): check
                   for check in checks}
        results = []
        for fut in futures:  # report in submission (deterministic) order
            try:
                res = fut.result()
            except subprocess.TimeoutExpired:
                check = futures[fut]
                res = {"check": check, "passed": False, "exit_code": -1,
                       "log": str(log_dir / f"{check}.timeout"),
                       "skipped": 0,
                       "summary": f"TIMEOUT after {1800}s"}
                (log_dir / f"{check}.timeout").write_text("timeout")
            print(f"[check] {res['check']} ... "
                  + ("PASS" if res["passed"] else "FAIL")
                  + f" ({res['exit_code']})  {res['summary']}")
            results.append(res)

    failed = [r for r in results if not r["passed"]]
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=str(REPO), capture_output=True, text=True,
                             timeout=15).stdout.strip()
    except Exception:
        rev = "unknown"
    evidence = {
        "ok": not failed, "when": stamp, "revision": rev,
        "set": "fast" if args.fast else "full",
        "checks": [{"check": r["check"], "passed": r["passed"],
                    "exit_code": r["exit_code"],
                    "skipped": r.get("skipped", 0)} for r in results],
    }
    # tracked evidence travels with commits (small, machine-neutral)
    checks_dir = REPO / "checks"
    checks_dir.mkdir(exist_ok=True)
    (checks_dir / "latest.json").write_text(json.dumps(evidence, indent=2))
    last = {"ok": not failed, "when": stamp,
            "passed": [r["check"] for r in results if r["passed"]],
            "failed": [{"check": r["check"], "exit_code": r["exit_code"],
                        "log": r["log"]} for r in failed]}
    (REPO / "logs" / "last_run.json").write_text(json.dumps(last, indent=2))

    print("-" * 60)
    if failed:
        print(f"REQUIRED CHECKS FAILED: {', '.join(r['check'] for r in failed)}")
        print(f"complete logs: {log_dir}")
        print("commit and push are BLOCKED until these pass.")
    else:
        print(f"all {len(results)} required checks passed. logs: {log_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
