import os
from pathlib import Path

REPO_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_PATH = REPO_ROOT / "src"
RECON_PATH = SRC_PATH / "recon"

MASS_SCAN_RUNNER_PATH = RECON_PATH / "MassScanRunner.py"
AUTO_RECON_RUNNER_PATH = RECON_PATH / "AutoReconRunner.py"
