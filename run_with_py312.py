"""
run_with_py312.py — Run any command inside Python 3.12 environment.

Ensures Python 3.12 is available (installs if missing), creates .venv,
then runs your command inside that environment. Original system PATH
is restored when the command exits (Windows subprocess isolation).

Usage:
    python run_with_py312.py pip install -r requirements.txt
    python run_with_py312.py main.py
    python run_with_py312.py python script.py

Any exit code from the child process is propagated.
"""

import sys
import os
import logging

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from python_env_manager import ensure_python312_env, run_in_env


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_with_py312.py <command> [args...]")
        print("")
        print("Examples:")
        print("  python run_with_py312.py pip install -r requirements.txt")
        print("  python run_with_py312.py python main.py")
        print("  python run_with_py312.py main.py")
        print("  python run_with_py312.py python -c \"print('hello')\"")
        sys.exit(1)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="[py312] %(message)s",
        stream=sys.stdout,
    )

    # First ensure Python 3.12 env exists
    logging.info("Checking Python 3.12 environment...")
    env_info = ensure_python312_env()
    if not env_info["ok"]:
        print(f"\nERROR: {env_info['error']}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Please install Python 3.12 manually from:", file=sys.stderr)
        print("  https://www.python.org/downloads/release/python-3129/", file=sys.stderr)
        sys.exit(1)

    # Resolve command to use venv's python/pip
    command = sys.argv[1:]
    first_arg = command[0].lower()

    if first_arg in ("python", "py"):
        # Replace with venv python.exe
        command = [env_info["python"]] + command[1:]
    elif first_arg == "pip":
        # Replace with venv pip.exe
        pip_path = env_info.get("pip")
        if pip_path and os.path.isfile(pip_path):
            command = [pip_path] + command[1:]
        else:
            command = [env_info["python"], "-m", "pip"] + command[1:]
    elif command[0].endswith(".py") or "main" in command[0]:
        # Auto-prepend python for .py scripts
        command = [env_info["python"]] + command

    exit_code = run_in_env(command, env_info=env_info)

    if exit_code != 0:
        logging.warning("Command exited with code %d", exit_code)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()