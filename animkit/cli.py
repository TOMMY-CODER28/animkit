"""animkit command-line interface.

Every subcommand returns (exit_code, result_dict). The dict always carries:
  ok, status, command, errors[], warnings[], next_actions[]
and is printed as friendly text, or as JSON with --json.
"""

from __future__ import annotations

import argparse
import json
import sys

from animkit import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="animkit",
        description="Reusable harness for AI-driven ManimGL animations: "
                    "brief -> validate -> preview -> frames -> inspect -> render -> deliver",
    )
    parser.add_argument("--json", action="store_true", help="print the structured result as JSON")
    parser.add_argument("--version", action="version", version=f"animkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="check environment: python, manimgl, ffmpeg, modules, latex")
    p.add_argument("--smoke", action="store_true", help="also render a 1s scene end-to-end (~15s)")

    p = sub.add_parser("check-layout", help="dry-run a spec-driven scene: validate + solve + geometry-check, no render")
    p.add_argument("project", nargs="?", default=".", help="project directory (default: .)")

    p = sub.add_parser("audio", help="generate stage narration WAVs (Kokoro TTS) + manifest")
    p.add_argument("project", nargs="?", default=".", help="project directory (default: .)")
    p.add_argument("--voice", help="Kokoro voice (default: spec.audio.voice or af_heart)")
    p.add_argument("--speed", type=float, help="speech speed multiplier (default 1.0)")
    p.add_argument("--lang", help="language code: 'a' American English, 'b' British, ...")
    p.add_argument("--force", action="store_true", help="regenerate even if cached")

    p = sub.add_parser("new", help="create a project from template")
    p.add_argument("name", help="project name, e.g. 'fourier-intro'")
    p.add_argument("--dir", default=".", help="parent directory for the new project (default: .)")
    p.add_argument("--force", action="store_true", help="overwrite existing target")

    for cmd, helptext in (
        ("validate", "validate project.json, files, scene code (+ --deep import check)"),
        ("preview", "fast low-quality render for inspection"),
        ("render", "final high-quality render"),
        ("frames", "extract representative frames from the latest video"),
        ("report", "summarize runs, outputs, and next actions"),
        ("deliver", "package video + source + reproduction steps"),
    ):
        p = sub.add_parser(cmd, help=helptext)
        p.add_argument("project", nargs="?", default=".", help="project directory (default: .)")
        if cmd in ("preview", "render"):
            p.add_argument("--scene", help="override scene class name from project.json")
        if cmd == "validate":
            p.add_argument("--deep", action="store_true", help="also import scene.py in a subprocess")
        if cmd == "frames":
            p.add_argument("--video", help="explicit video path (default: newest from runs index)")
            p.add_argument("--count", type=int, default=6, help="number of evenly spaced frames")
            p.add_argument("--at", help="comma-separated fractions, e.g. '0.1,0.5,0.9' (overrides --count)")
        if cmd == "deliver":
            p.add_argument("--dest", help="destination directory (default: <project>/deliverables/<name>)")
            p.add_argument("--run", default="latest", help="run id whose video to package")
    return parser


def _print_result(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2))
        return
    icons = {"success": "[ok]", "failure": "[FAIL]", "timeout": "[TIMEOUT]", "config_error": "[CONFIG ERROR]"}
    print(f"animkit {result.get('command')}: {icons.get(result.get('status'), '[?]')} {result.get('status')}")
    if result.get("project"):
        print(f"  project: {result['project']}")
    for err in result.get("errors", []):
        print(f"  error: {err}")
    for line in result.get("error_excerpt", [])[-8:]:
        print(f"    | {line}")
    for warn in result.get("warnings", []):
        print(f"  warning: {warn}")
    for label, value in (result.get("outputs") or {}).items():
        if isinstance(value, str):
            print(f"  {label}: {value}")
    details = result.get("details") or {}
    for key in ("resolution", "fps", "video_meta", "wall_s"):
        if key in details:
            print(f"  {key}: {details[key]}")
    if "frames" in details:
        print(f"  frames: {len(details['frames'])} extracted")
    if isinstance(result.get("details"), dict) and "run_count" in result["details"]:
        print(f"  runs recorded: {result['details']['run_count']}, videos: {len(result['outputs'].get('videos', []))}")
    if result.get("run"):
        print(f"  log: {result['run']['log']}")
    for action in result.get("next_actions", []):
        print(f"  next: {action}")


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        from animkit.commands import check
        code, result = check.run(args)
    elif args.command == "check-layout":
        from animkit.commands import check_layout
        code, result = check_layout.run(args)
    elif args.command == "audio":
        from animkit.commands import audio
        code, result = audio.run(args)
    elif args.command == "new":
        from animkit.commands import new
        code, result = new.run(args)
    elif args.command == "validate":
        from animkit.commands import validate
        code, result = validate.run(args)
    elif args.command in ("preview", "render"):
        from animkit.commands import render
        args.mode = "preview" if args.command == "preview" else "final"
        code, result = render.run(args)
    elif args.command == "frames":
        from animkit.commands import frames
        code, result = frames.run(args)
    elif args.command == "report":
        from animkit.commands import report
        code, result = report.run(args)
    elif args.command == "deliver":
        from animkit.commands import deliver
        code, result = deliver.run(args)
    else:  # pragma: no cover
        parser.error(f"unknown command {args.command}")

    _print_result(result, as_json=args.json)
    return code


if __name__ == "__main__":
    sys.exit(main())
