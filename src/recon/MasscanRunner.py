import argparse
import subprocess
from pathlib import Path
import re

def run_leftover_finder(project_folder):
    project_folder = Path(project_folder)
    recon_dir = project_folder / "recon/stage_2"
    chunks_dir = recon_dir / "chunks"
    processed_dir = recon_dir / "processed_chunks"
    processed_dir.mkdir(parents=True, exist_ok=True)

    all_open_hosts = set()

    for chunk_file in chunks_dir.glob("*.txt"):
        chunk_name = chunk_file.stem.replace("leftover_hosts_", "")
        output_masscan = processed_dir / f"found_quick_leftover_hosts_{chunk_name}.gnmap"

        # Run Masscan if output doesn't exist
        if not output_masscan.exists():
            cmd = (
                f"masscan -p0-65535 --rate {args.rate} --retries {args.retries} --wait {args.wait} "
                f"-v -iL {chunk_file} -oG {output_masscan} 2>/dev/null "
            )
            subprocess.run(cmd, shell=True, check=True)

        # Parse Masscan GNMAP output
        with open(output_masscan, "r") as f:
            for line in f:
                if line.startswith("Timestamp:") and "open" in line:
                    ip_match = re.search(r"Host:\s+(\S+)", line)
                    if ip_match:
                        ip = ip_match.group(1)
                        all_open_hosts.add(ip)

    # Save merged open hosts
    merged_file = recon_dir / "found_quick_leftover_hosts.txt"
    with open(merged_file, "w") as f:
        for ip in sorted(all_open_hosts):
            f.write(ip + "\n")

    print(f"[+] Total hosts with open ports: {len(all_open_hosts)} (saved to {merged_file})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Path to project folder")
    parser.add_argument("--rate", type=int, default=10000, help="Rate for Masscan")
    parser.add_argument("--retries", type=int, default=1, help="Retries for Masscan")
    parser.add_argument("--wait", type=int, default=10, help="Wait time for Masscan")
    args = parser.parse_args()
    run_leftover_finder(args.project)
