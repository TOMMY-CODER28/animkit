"""Focused animkit CLI tests: config errors, render failures, timeouts, reporting.

Run with the manim venv python:
  <manim-venv>\\Scripts\\python.exe tests\\test_cli.py
Exit 0 = all tests passed. Tests create and clean a temp area under tests/_tmp.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ANIMKIT = [sys.executable, "-m", "animkit"]  # run with same interpreter
ENV = {"PYTHONPATH": str(REPO), **{k: v for k, v in __import__('os').environ.items()}}

PASS, FAIL = [], []


def run_cli(*args, cwd=None):
    proc = subprocess.run(
        ANIMKIT + ["--json"] + list(args),
        capture_output=True, text=True, timeout=600, cwd=str(cwd or REPO),
        encoding="utf-8", errors="replace", env=ENV,
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {"_parse_error": proc.stdout[-500:], "stderr": proc.stderr[-500:]}
    return proc.returncode, result


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print(("PASS " if condition else "FAIL ") + name + (f"  [{detail}]" if detail and not condition else ""))


def main():
    tmp = Path(tempfile.mkdtemp(prefix="animkit_test_"))
    try:
        # ---- 1. check command reports environment --------------------------
        code, res = run_cli("check")
        check("check: exit 0 and ok", code == 0 and res.get("ok") is True)
        check("check: has manimgl version", bool(res["environment"]["manimgl_version"]))

        # ---- 2. new + validate happy path ----------------------------------
        proj = tmp / "t-proj"
        code, res = run_cli("new", "t-proj", "--dir", str(tmp))
        check("new: exit 0", code == 0)
        check("new: substituted scene class", res["details"]["scene_class"] == "TProj")
        code, res = run_cli("validate", str(proj))
        check("validate fresh project: exit 0", code == 0)

        # ---- 3. config errors ------------------------------------------------
        bad_name = proj / "project.json"
        cfg = json.loads(bad_name.read_text())
        cfg["name"] = "bad name with spaces"
        bad_name.write_text(json.dumps(cfg))
        code, res = run_cli("validate", str(proj))
        check("config error: exit 2", code == 2, f"code={code}")
        check("config error: status config_error", res.get("status") == "config_error")
        check("config error: has errors list", isinstance(res.get("errors"), list) and res["errors"])

        cfg["name"] = "t-proj"
        cfg["output"]["final_resolution"] = [1919, 1080]  # odd width
        bad_name.write_text(json.dumps(cfg))
        code, res = run_cli("validate", str(proj))
        check("odd resolution rejected", code == 2 and any("even" in e for e in res["errors"]))

        bad_name.unlink()
        code, res = run_cli("validate", str(proj))
        check("missing project.json: exit 2 with message", code == 2 and "project.json" in res["errors"][0])

        code, res = run_cli("new", "bad name!", "--dir", str(tmp))
        check("new rejects bad name: exit 2", code == 2)

        # ---- 4. scene mismatch caught by validate ---------------------------
        code, _ = run_cli("new", "mismatch", "--dir", str(tmp))
        scene_p = tmp / "mismatch" / "scene.py"
        scene_p.write_text(scene_p.read_text().replace("class Mismatch(", "class Renamed("))
        code, res = run_cli("validate", str(tmp / "mismatch"))
        check("scene/class mismatch detected",
              code == 1 and any("Mismatch" in e and "Renamed" in e for e in res["errors"]))

        # ---- 5. render failure: broken scene ---------------------------------
        code, _ = run_cli("new", "broken", "--dir", str(tmp))
        bp = tmp / "broken" / "scene.py"
        bp.write_text("from manimlib import *\n\nclass Broken(Scene):\n    def construct(self):\n        self.play(DoesNotExist())\n")
        code, res = run_cli("preview", str(tmp / "broken"))
        check("render failure: exit 1", code == 1, f"code={code}")
        check("render failure: status failure", res.get("status") == "failure")
        check("render failure: error_excerpt present", bool(res.get("error_excerpt")))
        check("render failure: no video output", not (res.get("outputs") or {}).get("video"))

        # ---- 6. timeout path ---------------------------------------------------
        code, _ = run_cli("new", "slow", "--dir", str(tmp))
        sp_ = tmp / "slow" / "project.json"
        cfg = json.loads(sp_.read_text())
        cfg["timing"]["preview_timeout_s"] = 2
        sp_.write_text(json.dumps(cfg))
        (tmp / "slow" / "scene.py").write_text(
            "from manimlib import *\n\nclass Slow(Scene):\n"
            "    def construct(self):\n"
            "        t = Text('x', font_size=20)\n"
            "        self.add(t)\n"
            "        for _ in range(400):\n"
            "            self.play(t.animate.shift(0.01*RIGHT), run_time=0.1)\n"
        )
        code, res = run_cli("preview", str(tmp / "slow"))
        check("timeout: exit 3 / status timeout", code == 3 or res.get("status") == "timeout",
              f"code={code} status={res.get('status')}")

        # ---- 7. frames without video -------------------------------------------
        code, _ = run_cli("new", "novideo", "--dir", str(tmp))
        code, res = run_cli("frames", str(tmp / "novideo"))
        check("frames without render: exit 1 + next action", code == 1 and res.get("next_actions"))

        # ---- 8. report on a real project (example 1) ---------------------------
        ex1 = REPO / "examples" / "equal-area-shapes"
        if ex1.is_dir():
            code, res = run_cli("report", str(ex1))
            check("report: exit 0, lists runs", code == 0 and res["details"]["run_count"] >= 1)
            check("report: lists videos", len(res["outputs"]["videos"]) >= 1)

        # ---- 9. deliver on a real project ---------------------------------------
        code, res = run_cli("deliver", str(ex1), "--dest", str(tmp / "pkg"))
        check("deliver: exit 0 with files", code == 0 and Path(res["outputs"]["video"]).is_file())
        check("deliver: REPRODUCE.md written", Path(res["outputs"]["reproduce"]).is_file())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
