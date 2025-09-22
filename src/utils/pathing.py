import os
from pathlib import Path

REPO_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_PATH = REPO_ROOT / "src"
RECON_PATH = SRC_PATH / "recon"
EXTERNAL_TOOLS_PATH = REPO_ROOT / "external"
AUTORECON_REPO_PATH = EXTERNAL_TOOLS_PATH / "AutoRecon"
AUTORECON_PY_PATH = AUTORECON_REPO_PATH / "autorecon.py"
VENV_PATH = REPO_ROOT / ".venv"
VENV_PYTHON_PATH = VENV_PATH / "bin" / "python"

MASS_SCAN_RUNNER_PATH = RECON_PATH / "MassScanRunner.py"
AUTO_RECON_RUNNER_PATH = RECON_PATH / "AutoReconRunner.py"
