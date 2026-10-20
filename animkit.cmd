@echo off
rem animkit launcher: routes through the ManimGL venv so av / Pillow /
rem imageio_ffmpeg are importable. Resolution order:
rem   1. ANIMKIT_PYTHON env var (venv python.exe)
rem   2. python.exe next to a manimgl.exe found via ANIMKIT_MANIMGL
rem   3. the sibling venv "manim\.venv" (this project's historical layout)
rem   4. an installed `animkit` console script on PATH
setlocal
set "ANIMKIT_HOME=%~dp0"

if defined ANIMKIT_PYTHON goto :run
rem NB: search the .exe console script only — `where animkit` would match
rem THIS .cmd file in the current directory and recurse forever
where animkit.exe >nul 2>nul && (animkit.exe %* & exit /b %ERRORLEVEL%)

set "CAND=%ANIMKIT_HOME%..\.venv\Scripts\python.exe"
if not exist "%CAND%" set "CAND=%ANIMKIT_HOME%.venv\Scripts\python.exe"
if not exist "%CAND%" set "CAND=<manim-venv>\Scripts\python.exe"
if exist "%CAND%" (set "PY=%CAND%") else (
  echo [animkit] no ManimGL venv found. Set ANIMKIT_PYTHON to the venv's
  echo [animkit] python.exe, or "pip install -e ." animkit into the venv and
  echo [animkit] use the `animkit` command directly.
  exit /b 2
)

:run
if not defined PY set "PY=%ANIMKIT_PYTHON%"
set "PYTHONPATH=%ANIMKIT_HOME%;%PYTHONPATH%"
"%PY%" -m animkit %*
exit /b %ERRORLEVEL%
