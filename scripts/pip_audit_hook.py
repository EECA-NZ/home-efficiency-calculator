#!/usr/bin/env python3
"""
This script is a pre-commit hook that ensures the user is in a venv,
updates dev requirements, and then runs pip-audit to check for known vulnerabilities.
"""

import os
import subprocess
import sys


def main():
    """
    Main entry point for pip-audit hook.
    Checks if we're in a venv, installs dev requirements, and runs pip-audit.
    """
    # 1) Check if we are inside a virtual environment
    if "VIRTUAL_ENV" not in os.environ:
        print("ERROR: You must activate a local .venv before committing.")
        sys.exit(1)
    # 2) Install/Update requirements-dev.txt
    try:
        subprocess.check_call(["pip", "install", "-r", "requirements-dev.txt"])
    except subprocess.CalledProcessError as e:
        print("Failed to install requirements-dev.txt.")
        sys.exit(e.returncode)
    # 3) Run pip-audit on the active environment
    try:
        subprocess.check_call(["pip-audit"])
    except subprocess.CalledProcessError as e:
        print("pip-audit found vulnerabilities or failed.")
        sys.exit(e.returncode)

    print("Environment updated; no known vulnerabilities found.")
    sys.exit(0)


if __name__ == "__main__":
    main()
