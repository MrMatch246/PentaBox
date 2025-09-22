#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

# Import paths from your pathing file
sys.path.append(str(Path(__file__).parent / "src" / "utils"))
from src.utils.pathing import (
    REPO_ROOT,
    EXTERNAL_TOOLS_PATH,
    AUTORECON_REPO_PATH,
    VENV_PATH,
    VENV_PYTHON_PATH,
)


def run_command(command, cwd=None):
    """Run a shell command and exit if it fails."""
    print(f"[+] Running: {' '.join(command)}")
    try:
        subprocess.run(command, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Command failed with exit code {e.returncode}: {' '.join(command)}")
        sys.exit(e.returncode)

def clone_or_update_autorecon():
    """Clone AutoRecon if missing, otherwise pull the latest changes."""
    if AUTORECON_REPO_PATH.exists():
        print(f"[+] Updating AutoRecon in {AUTORECON_REPO_PATH}")
        run_command(["git", "pull"], cwd=AUTORECON_REPO_PATH)
    else:
        print(f"[+] Cloning AutoRecon into {AUTORECON_REPO_PATH}")
        EXTERNAL_TOOLS_PATH.mkdir(parents=True, exist_ok=True)
        run_command(["git", "clone", "https://github.com/MrMatch246/AutoRecon", str(AUTORECON_REPO_PATH)])

def create_venv_if_missing():
    """Create Python virtual environment only if not already present."""
    if VENV_PATH.exists():
        print(f"[+] Virtual environment already exists at {VENV_PATH}")
    else:
        print(f"[+] Creating virtual environment at {VENV_PATH}")
        run_command([sys.executable, "-m", "venv", str(VENV_PATH)])

def install_requirements_if_needed():
    """Install requirements only if venv was just created or pip packages missing."""
    requirements_file = REPO_ROOT / "requirements.txt"
    if not requirements_file.exists():
        print(f"[!] requirements.txt not found at {requirements_file}")
        sys.exit(1)
    print(f"[+] Ensuring requirements are installed")
    run_command([str(VENV_PYTHON_PATH), "-m", "pip", "install", "--upgrade", "pip"])
    run_command([str(VENV_PYTHON_PATH), "-m", "pip", "install", "-r", str(requirements_file)])

def main():
    print(f"[+] Setting up repository at {REPO_ROOT}")
    clone_or_update_autorecon()
    create_venv_if_missing()
    install_requirements_if_needed()
    print("[+] Setup complete! External tools are up-to-date.")

if __name__ == "__main__":
    main()
