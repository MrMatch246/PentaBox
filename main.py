import argparse
from src.pentabox import PentaBox

# ------------------------
# CLI Entrypoint with Subcommands
# ------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Pentest Automation Script")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # ------------------------
    # Recon Command
    # ------------------------
    recon_parser = subparsers.add_parser("recon", help="Run reconnaissance phase")
    recon_parser.add_argument("--bypass-tmux", action="store_true", help="Bypass tmux check")
    recon_parser.add_argument("--project", type=str, help="Path to project folder")
    recon_parser.add_argument("--here", action="store_true", help="Use current directory as project folder")
    recon_parser.add_argument("--target", type=str, required=True, help="Path/IP/domain for target(s)")
    recon_parser.add_argument("--force-phase", action="store_true", help="Force rerun of phases")
    recon_parser.add_argument("--hosts", type=str, help="Path to file with list of known hosts", default=None)
    recon_parser.add_argument("--skip-ip-check", action="store_true", help="Skip IP verification")
    recon_parser.add_argument("--config", type=str, help="Path to JSON config file")

    # ------------------------
    # Exploit Command
    # ------------------------
    #exploit_parser = subparsers.add_parser("exploit", help="Run exploitation phase")
    #exploit_parser.add_argument("--project", type=str, help="Path to project folder")
    #exploit_parser.add_argument("--here", action="store_true", help="Use current directory as project folder")
    #exploit_parser.add_argument("--target", type=str, required=True, help="Path/IP/domain for target(s)")
    #exploit_parser.add_argument("--config", type=str, help="Path to JSON config file")

    # ------------------------
    # Report Command
    # ------------------------
    #report_parser = subparsers.add_parser("report", help="Generate final report")
    #report_parser.add_argument("--project", type=str, required=True, help="Path to project folder")
    #report_parser.add_argument("--config", type=str, help="Path to JSON config file")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    PentaBox(args).run()
