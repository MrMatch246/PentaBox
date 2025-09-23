import argparse



from src.pentabox import PentaBox


# ------------------------
# CLI Entrypoint
# ------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Pentest Automation Script")
    parser.add_argument("--bypass-tmux", action="store_true", help="Bypass tmux check")
    parser.add_argument("--project", type=str, help="Path to project folder")
    parser.add_argument("--here", action="store_true", help="Use current directory as project folder")
    parser.add_argument("--target", type=str, help="Path/IP/domain for target(s)")
    parser.add_argument("--force-phase", action="store_true", help="Force rerun of phases")
    parser.add_argument("--hosts" , type=str, help="Path to file with list of known hosts",default=None)
    parser.add_argument("--skip-ip-check", action="store_true", help="Skip IP verification")
    parser.add_argument("--config", type=str, help="Path to JSON config file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    PentaBox(args).run()

