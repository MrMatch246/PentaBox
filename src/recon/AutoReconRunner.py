import argparse
import subprocess
import sys
from pathlib import Path

# Add the repo root to sys.path so `import src.*` works even when running the script directly
REPO_ROOT = Path(__file__).resolve().parents[2]  # go two levels up from src/recon/
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils.pathing import AUTORECON_PY_PATH, VENV_PYTHON_PATH


def run_autorecon(project_folder, hosts_file, config=None, targets=None, autorecon_config=None):
    project_folder = Path(project_folder)
    output_dir = project_folder / "recon/hosts"
    stage_3_dir = project_folder / "recon/stage_3"
    stage_3_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Targets arg is currently unused, but might be used in the future to group hosts
    # by the original targets file.
    # that means all hosts that are part of one target in the targets file will
    # be stored under the same directory named after the target.
    # here one should also additionally employ chunking, which is the reason why
    # the targets argument is currently unused.
    if targets:
        raise NotImplementedError("targets not implemented")

    # Run AutoRecon
    autorecon_bin = [VENV_PYTHON_PATH, AUTORECON_PY_PATH]  # Adjust this if AutoRecon is not in PATH
    autorecon_bin.extend(["-t", hosts_file, "-o", str(output_dir),"-vv"])
    cmd = autorecon_bin
    if config:
        cmd.extend(["--config", config])
    if autorecon_config:
        raise NotImplementedError("autorecon_config is not implemented yet")

    subprocess.run(cmd, check=True)

    # Drop marker file in stage_3
    hosts_path_str = str(hosts_file).lower()
    if "masscan" in hosts_path_str:
        marker_file = stage_3_dir / ".autorecon_masscan"
    elif "leftover" in hosts_path_str:
        marker_file = stage_3_dir / ".autorecon_leftover"
    else:
        marker_file = stage_3_dir / ".autorecon_unknown"

    marker_file.touch()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--hosts", required=True)
    parser.add_argument("--config", help="Config file for AutoRecon")
    parser.add_argument("--targets", help="Original targets file")
    parser.add_argument("--autorecon-config", help="Config file for AutoRecon scan parameters")
    args = parser.parse_args()
    run_autorecon(args.project, args.hosts, args.config, args.targets, args.autorecon_config)
