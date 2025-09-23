
# Phase: Recon
# Stage 0: Setup
# We will then check if there is an arg provided for the project folder (relative or absolute path).
# --project <path>
# now for each completed Stage we will create a file called .stage<x> in project_folder/recon.
# in the following Stages we will always first check if the file exists and if it does we will skip that stage,
# unless there is a flag to force the stage to run again. --run-stage x
# This will also re-run all following stages.
# First we will try to load the self.project_data from the <project_folder>/<project_folder>.json file,
# then we will load the self.phase_config from self.project_data["config"]["phases"]["recon"].
# here we will also load the self.stages from self.project_data["config"]["phases"]["recon"]["stages"],
# and self.project_general config from self.project_data["config"]["general"].
# and finally we will load the self.phase_general config from self.project_data["config"]["phases"]["recon"]["general"].
# for each config we will default to an empty dict if the key is not present.
# it might be that even the self.project_data["config"] is not present,
# in that case we will create an empty dict for self.project_data["config"] and so on.
#
#
# Stage 1: Mass Host Discovery
# In this stage we will use masscan to discover hosts in the target network.
# In all the following a target describes a single line in the <project_folder>/scope/targets.txt file.
# The targets can be a single IP, a range of IPs or a CIDR notation or a domain name.
# To discover live hosts fast we will use masscan:
# sudo masscan <project_folder>/scope/targets.txt -p80,443 --ping --retries 1 --wait 10 --rate=<rate> --open [2>/dev/null] | awk '{print $6}'
# and capture the output and write into <project_folder>/recon/stage_1/masscan_hosts.txt
#
#
# Stage 2: Quick Leftover Host Discovery
# If there is already a file called <project_folder>/recon/stage_2/found_quick_leftover_hosts.gnmap we will skip Stage 2.
# The first part of this stage will be to discover hosts that were not found in the previous stage.
# For this we will compose a list of all IPs in the target networks, minus the ones that were found in the previous stage.
# These are then split into chunks of <chunk_size> IPs, where <chunk_size> is defined in the self.stages["stage_2"]["host_discovery"]["chunk-size"] config.
# for example if the target is a.b.c.0/24 and <chunk_size> is 50,
# we will create chunks like this:
# a.b.c.0-a.b.c.49, a.b.c.50-a.b.c.99... (.255 is not included)
#
# We will then, for each chunk of each target, create a file called <project_folder>/recon/stage_2/chunks/leftover_hosts_a.b.c.<start>-a.b.c.<end>.txt
# if a target is only a single IP, we will create a file called <project_folder>/recon/stage_2/chunks/leftover_hosts_<ip>.txt
# Now for all chunks that havent been processed yet, which means the file <project_folder>/recon/stage_2/processed_chunks/found_quick_leftover_hosts_<chunk>.gnmap does not exist,
# we will spawn a python process (NmapRunner - LeftoverFinder) that goes through the list of all chunks and runs nmap on each one using the leftover_hosts_<chunk>.txt file as input.
# As we dont need any direct output from this process we will run it in the background and detach it.
# The nmap command will be:
# nmap -sn -n -Pn --top-ports 100 -iL <project_folder>/recon/stage_2/chunks/leftover_hosts_<chunk>.txt -oG <project_folder>/recon/stage_2/processed_chunks/found_quick_leftover_hosts_<chunk>.gnmap
# After all chunks have been processed we will merge all found_leftover_hosts_<subnet>.gnmap files into one file called <project_folder>/recon/stage_2/found_quick_leftover_hosts.txt
# containing only the IPs of the hosts that were found in the previous stage.
# Now once we have the leftover hosts we will use them, too, as input for Stage 3.
# This includes using a file watcher to monitor the <project_folder>/recon/stage_2/found_quick_leftover_hosts.txt file for creation.
#
# Stage 3: Deep Scanning
# This stage starts immediately after LeftoverFinder has been started and detached.
# Here we will spawn a named Tmux session (or attach to it if it already exists) called autorecon-mass-scan.
# using this session we will run the AutoReconRunner (DeepScanner) to scan the hosts that were found in Stage 1.
# while being able to monitor the progress in real-time and meanwhile also being able to monitor the leftover hosts discovery in Stage 2.
# The AutoReconRunner (DeepScanner) Python script will be given a file containing the live hosts to scan,
# which is --hosts <project_folder>/recon/stage_1/masscan_hosts.txt,
# a --config as defined in the self.stages["stage_2"]["autorecon-scan"] (optional),
# the original --targets <project_folder>/scope/targets.txt file,
# and optionally a config for autorecon defined in the self.stages["stage_2"]["autorecon-scan"]["autorecon"] config.
# and via --output-dir <project_folder>/recon/hosts as output directory.
# After the AutoReconRunner (DeepMassScanner) has been started in the autorecon-mass-scan tmux session, we will detach from it,
# and then we will monitor the <project_folder>/recon/stage_2/ folder for the creation of the file <project_folder>/recon/stage_2/found_quick_leftover_hosts.txt.
# Once this file is created, we will spawn another tmux session (or attach to it if it already exists) called autorecon-leftover-scan.
# And again we will run the AutoReconRunner (DeepLeftoverScanner) to scan the leftover hosts that were found in Stage 2.
# this time we will use the file <project_folder>/recon/stage_2/found_quick_leftover_hosts.txt as --hosts input.
#
#



import json
import os
import time

from src.recon.MassScanRunner import *
from src.recon.AutoReconRunner import *
from src.utils.base import BaseClass
from src.utils import *
from src.utils.pathing import *
from src.utils.tmux import TmuxSession



class Recon(BaseClass):
    def __init__(self,project_path, run_stage=None,hosts_override=None):
        super().__init__(project_path)
        self.autorecon_leftover_scan = None
        self.masscan_leftover_finder = None
        self.autorecon_mass_scan = None
        self.hosts_override = hosts_override
        #self.logger = self.convenient_logging.getLogger(name="recon", level="DEBUG")
        self.project_folder = Path(project_path).resolve()
        self.run_stage = run_stage
        self.recon_folder = self.project_folder / "recon"
        self.stages_folder = self.recon_folder
        self.scope_file = self.project_folder / "scope" / "targets.txt"
        self.has_leftovers = False

        # Ensure recon directory exists
        self.recon_folder.mkdir(parents=True, exist_ok=True)

        # Load project data and config
        self.project_data = self.load_project_data()
        self.phase_config = self.project_data.get("config", {}).get("phases", {}).get("recon", {})
        self.stages = self.phase_config.get("stages", {})
        self.project_general = self.project_data.get("config", {}).get("general", {})
        self.phase_general = self.phase_config.get("general", {})


    def load_project_data(self):
        project_json = self.project_folder / f"{self.project_folder.name}.json"
        if project_json.exists():
            with open(project_json, "r") as f:
                return json.load(f)
        return {}

    def stage_marker(self, stage):
        return self.recon_folder / f".stage{stage}"

    def run(self):
        # Stage 0 Setup is implicit here (loading configs)
        try:
            if self.should_run_stage(1):
                self.run_stage_1()
            if self.should_run_stage(2):
                self.run_stage_2()
            if self.should_run_stage(3):
                self.run_stage_3()
        except KeyboardInterrupt:
            self.keyboard_interrupt_handler()

    def keyboard_interrupt_handler(self):
        if self.autorecon_leftover_scan:
            self.autorecon_leftover_scan.kill()
        if self.masscan_leftover_finder:
            self.masscan_leftover_finder.kill()
        if self.autorecon_mass_scan:
            self.autorecon_mass_scan.kill()
        original_user = os.environ.get("SUDO_USER")
        if original_user:
            os.system(f"sudo chown {original_user}:{original_user} -R {self.project_path}")
        self.critical("KeyboardInterrupt received. Exiting gracefully.")


    def should_run_stage(self, stage):
        marker = self.stage_marker(stage)
        if self.run_stage and stage >= self.run_stage:
            return True
        return not marker.exists()

    def mark_stage_complete(self, stage):
        self.stage_marker(stage).touch()

    # Stage 1: Mass Host Discovery
    def run_stage_1(self):
        self.info("[*] Running Stage 1: Mass Host Discovery")
        stage_dir = self.recon_folder / "stage_1"
        stage_dir.mkdir(parents=True, exist_ok=True)
        output_file = stage_dir / "masscan_hosts.txt"
        rate = self.stages.get("stage_1", {}).get("masscan", {}).get("rate", "10000")
        cmd = (
            f"sudo masscan -iL {self.scope_file} -p80,443 --ping --retries 1 --wait 10 --rate {rate} --open 2>/dev/null "
            f"| awk '{{print $6}}' | sort -u > {output_file}"
        )
        if not self.hosts_override:
            with self.console().status("[byellow] Running Masscan for host discovery..."):
                subprocess.run(cmd, shell=True, check=True)
        else:
            self.info(f"[*] Using host override, skipping masscan. Writing to {output_file}")
            with open(output_file, "w") as f:
                with open(self.hosts_override, "r") as hf:
                    hosts = [line.strip() for line in hf if line.strip()]
                    f.write("\n".join(hosts) + "\n")

        self.mark_stage_complete(1)


    # Stage 2: Quick Leftover Host Discovery
    def run_stage_2(self):
        self.info("[*] Running Stage 2: Mass Leftover Host Discovery")
        stage_dir = self.recon_folder / "stage_2"
        chunks_dir = stage_dir / "chunks"
        processed_dir = stage_dir / "processed_chunks"
        stage_dir.mkdir(parents=True, exist_ok=True)
        chunks_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        leftover_file = stage_dir / "found_quick_leftover_hosts.txt"
        if leftover_file.exists() or self.hosts_override:
            return

        chunk_size = self.stages.get("stage_2", {}).get("host_discovery", {}).get("chunk-size", 50)
        rate = self.stages.get("stage_2", {}).get("host_discovery", {}).get("rate", "10000")
        # Generate chunks (using utility functions assumed available from toolboxes.pentesting.utils)
        live_hosts = load_lines(self.recon_folder / "stage_1/masscan_hosts.txt")
        targets = load_lines(self.scope_file)
        if generate_leftover_chunks(targets, live_hosts, chunk_size, chunks_dir):
            self.masscan_leftover_finder = TmuxSession("masscan-leftover-finder")
            self.masscan_leftover_finder.send_line(f"{VENV_PYTHON_PATH} {MASS_SCAN_RUNNER_PATH} --project {self.project_folder} --rate {rate}")
            self.has_leftovers = True

        self.mark_stage_complete(2)

    # Stage 3: Deep Scanning
    def run_stage_3(self):
        self.info("[*] Running Stage 3: Deep Scanning with AutoRecon")

        # Start AutoRecon for Stage 1 hosts
        hosts_file = self.recon_folder / "stage_1/masscan_hosts.txt"
        autorecon_mass_scan_done = self.project_path / "recon" / "stage_3" / ".autorecon_masscan"
        if not autorecon_mass_scan_done.exists():
            self.autorecon_mass_scan = TmuxSession("autorecon-mass-scan")
            cmd = f"{VENV_PYTHON_PATH} {AUTO_RECON_RUNNER_PATH} --project {self.project_folder} --hosts {hosts_file}"
            self.autorecon_mass_scan.send_line(cmd)
            self.info(f"[*] AutoRecon started for Stage 1 hosts in tmux session: autorecon-mass-scan")

        # Watch for leftover hosts and launch second scan
        leftover_file = self.recon_folder / "stage_2/found_quick_leftover_hosts.txt"
        discovery = False
        if not leftover_file.exists() and self.has_leftovers:
            self.info(f"[*] Waiting for completion of leftover host discovery: {leftover_file}")
            discovery = True
            with self.console().status(f"[byellow] Waiting for completion of leftover host discovery: {leftover_file}"):
                while not leftover_file.exists():
                    time.sleep(10)
                #TODO add logic here to check if any hosts were found, if not skip the leftover scan, set self.has_leftovers to False

        if self.has_leftovers:
            autorecon_leftover_done = self.project_path / "recon" / "stage_3" / ".autorecon_leftover"
            if not autorecon_leftover_done.exists() and leftover_file.exists():
                if discovery:
                    self.info(f"[*] Leftover host discovery completed. Starting leftover scan with AutoRecon.")
                else:
                    self.info(f"[*] Resuming Deep Scan of leftover hosts with AutoRecon.")
                tmux_session_leftover = "autorecon-leftover-scan"
                self.autorecon_leftover_scan = TmuxSession(tmux_session_leftover)
                self.autorecon_leftover_scan.send_line(f"{VENV_PYTHON_PATH} {AUTO_RECON_RUNNER_PATH} --project {self.project_folder} --hosts {leftover_file}")

        with self.console().status(f"[byellow] Waiting for AutoRecon to complete for Stage 1 hosts..."):
            while not autorecon_mass_scan_done.exists():
                time.sleep(10)

        if self.has_leftovers:
            with self.console().status(f"[byellow] Waiting for AutoRecon to complete for leftover hosts..."):
                while not autorecon_leftover_done.exists():
                    time.sleep(10)

        self.mark_stage_complete(3)

