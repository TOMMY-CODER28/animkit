#!/usr/bin/env bash
# animkit launcher (Git Bash / WSL / Linux / macOS). Resolution order:
#   1. ANIMKIT_PYTHON env var
#   2. an installed `animkit` console script on PATH
#   3. sibling venvs: ../.venv, ./.venv, ./manim/.venv (historical layout)
ANIMKIT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$ANIMKIT_PYTHON" ]; then PY="$ANIMKIT_PYTHON"
elif command -v animkit >/dev/null 2>&1; then exec animkit "$@"
elif [ -f "$ANIMKIT_HOME/../manim/.venv/bin/python" ]; then PY="$ANIMKIT_HOME/../manim/.venv/bin/python"
elif [ -f "$ANIMKIT_HOME/../.venv/bin/python" ]; then PY="$ANIMKIT_HOME/../.venv/bin/python"
elif [ -f "$ANIMKIT_HOME/.venv/bin/python" ]; then PY="$ANIMKIT_HOME/.venv/bin/python"
elif [ -f "$ANIMKIT_HOME/manim/.venv/bin/python" ]; then PY="$ANIMKIT_HOME/manim/.venv/bin/python"
elif [ -f "$ANIMKIT_HOME/.venv/Scripts/python.exe" ]; then PY="$ANIMKIT_HOME/.venv/Scripts/python.exe"
else
  echo "[animkit] no ManimGL venv found. Set ANIMKIT_PYTHON, or 'pip install -e .'" >&2
  echo "[animkit] animkit into the venv and use the \`animkit\` command directly." >&2
  exit 2
fi

PYTHONPATH="$ANIMKIT_HOME:$PYTHONPATH" "$PY" -m animkit "$@"
exit $?
