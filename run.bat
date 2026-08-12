@echo off
REM Convenience launcher for agent-bridge on Windows.
REM Usage:  run.bat --project D:\path\to\project [--manager manual|api|web|agent] [--iterations N]

set PYTHON=python
if defined PYTHON_PATH set PYTHON=%PYTHON_PATH%
%PYTHON% -m src %*