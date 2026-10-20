"""Run records: every render/inspect command gets a durable, traceable record.

Layout inside a project:
  runs/index.json          -- append-only list of run entries
  runs/0003-preview/       -- per-run directory
      log.txt              -- full subprocess output
      manim_config.yml     -- exact config handed to manimgl (for renders)
      result.json          -- structured result returned to the caller
      frames/              -- extracted PNGs (for the frames command)
"""

from __future__ import annotations

import datetime
import json
import subprocess
import time
from pathlib import Path
from typing import Sequence


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")


class Run:
    """One command execution against a project."""

    def __init__(self, project_root: Path, command: str):
        self.project_root = Path(project_root)
        self.runs_dir = self.project_root / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        index = self._read_index()
        seq = len(index.get("runs", [])) + 1
        # a killed run can leave an orphan dir with no result.json — skip it
        while (self.runs_dir / f"{seq:04d}-{command}").exists():
            seq += 1
        self.id = f"{seq:04d}-{command}"
        self.dir = self.runs_dir / self.id
        self.dir.mkdir(parents=True, exist_ok=False)
        self.log_path = self.dir / "log.txt"
        self._log = open(self.log_path, "w", encoding="utf-8", buffering=1)
        self._command = command
        self._started = time.time()
        self.log_line(f"animkit run {self.id}")
        self.log_line(f"started: {datetime.datetime.now().isoformat(timespec='seconds')}")

    # -- logging -------------------------------------------------------------
    def log_line(self, line: str) -> None:
        self._log.write(line + "\n")

    def log_argv(self, argv: Sequence[str]) -> None:
        self.log_line("command: " + " ".join(_quote(a) for a in argv))

    # -- subprocess ----------------------------------------------------------
    def run_subprocess(self, argv: Sequence[str], cwd: Path, timeout_s: int) -> dict:
        self.log_argv(argv)
        self.log_line(f"cwd: {cwd}")
        self.log_line(f"timeout_s: {timeout_s}")
        self.log_line("-" * 60)
        start = time.time()
        timed_out = False
        try:
            proc = subprocess.run(
                [str(a) for a in argv],
                cwd=str(cwd),
                stdout=self._log,
                stderr=subprocess.STDOUT,
                timeout=timeout_s,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            code = 124
            self.log_line(f"\n[animkit] TIMEOUT after {timeout_s}s — process killed")
        except Exception as exc:  # e.g. executable missing
            self.log_line(f"\n[animkit] failed to start process: {exc}")
            code = 127
        wall = round(time.time() - start, 1)
        self.log_line("-" * 60)
        self.log_line(f"exit_code: {code}, wall_seconds: {wall}")
        return {"exit_code": code, "timed_out": timed_out, "wall_s": wall}

    def error_excerpt(self, max_lines: int = 25) -> list[str]:
        """Tail of the log, for surfacing the actual failure in JSON results."""
        try:
            lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            return []
        tail = [ln.rstrip() for ln in lines[-max_lines:] if ln.strip()]
        return tail

    # -- closing -------------------------------------------------------------
    def write_result(self, result: dict) -> None:
        result = dict(result)
        result["run"] = {
            "id": self.id,
            "command": self._command,
            "dir": str(self.dir),
            "log": str(self.log_path),
            "wall_s": round(time.time() - self._started, 1),
        }
        (self.dir / "result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result

    def update_index(self, result: dict) -> None:
        entry = {
            "id": self.id,
            "command": self._command,
            "ok": result.get("ok", False),
            "status": result.get("status"),
            "wall_s": result.get("run", {}).get("wall_s"),
            "video": (result.get("outputs") or {}).get("video"),
            "started": _now(),
        }
        index = self._read_index()
        index.setdefault("runs", []).append(entry)
        (self.runs_dir / "index.json").write_text(
            json.dumps(index, indent=2), encoding="utf-8"
        )

    def close(self) -> None:
        try:
            self._log.close()
        except Exception:
            pass

    def _read_index(self) -> dict:
        path = self.runs_dir / "index.json"
        if not path.is_file():
            return {"runs": []}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"runs": []}


def read_index(project_root: Path) -> dict:
    path = Path(project_root) / "runs" / "index.json"
    if not path.is_file():
        return {"runs": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"runs": []}


def _quote(arg: str) -> str:
    return f'"{arg}"' if " " in arg else arg
