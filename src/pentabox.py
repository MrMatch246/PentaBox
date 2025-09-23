import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from rich.prompt import Confirm, Prompt

from src.recon.recon import Recon
from src.utils import is_in_tmux, get_internal_ip, get_external_ip, md5_hash
from src.utils.base import BaseClass


class PentaBox(BaseClass):
    def __init__(self, args):
        super().__init__(self._resolve_project_path(args))
        #self.logger = self.convenient_logging.getLogger(name="pentest_phase0_setup", level="DEBUG")
        self.args = args
        self.project_json = self.project_path / f".{self.project_path.name}.json"
        self.project_data = {}

    # ------------------------
    # Initialization Helpers
    # ------------------------
    def _resolve_project_path(self,args):

        if args.project:
            return Path(args.project).resolve()
        elif args.here:
            return Path.cwd()
        else:
            return Path.cwd() / f"pentest-{datetime.now().strftime('%Y-%m-%d')}"


    def _ensure_directories(self):
        self.project_path.mkdir(parents=True, exist_ok=True)
        (self.project_path / "logs").mkdir(exist_ok=True)

    def _check_tmux(self):
        if not self.args.bypass_tmux and not is_in_tmux():
            self.critical("[bold red]This script should be run inside tmux. Use --bypass-tmux to skip this check.")

    def _phase_done(self, phase):
        (self.project_path / f".phase_{phase}").touch()
        self.info(f"Phase {phase} marked as complete.")
        original_user = os.environ.get("SUDO_USER")
        if original_user:
            os.system(f"sudo chown {original_user}:{original_user} -R {self.project_path}")

    # ------------------------
    # Config Handling
    # ------------------------
    def handle_config(self):
        if not self.args.config:
            return

        config_path = Path(self.args.config)
        if not config_path.exists():
            self.critical(f"Config file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                new_config = json.load(f)
        except json.JSONDecodeError as e:
            self.critical(f"Failed to parse config file: {e}")

        if "general" not in new_config or "phases" not in new_config:
            self.critical("Config file must contain 'general' and 'phases' keys at the root.")

        if "config" not in self.project_data:
            self.project_data["config"] = new_config
            self.info("Config added to project data.")
        else:
            if self.project_data["config"] != new_config:
                self.warning("A different config is already present in project data.")
                if Confirm.ask("Replace existing config with the new one?"):
                    self.project_data["config"] = new_config
                    self.info("Config updated.")
                else:
                    self.info("Keeping existing config.")

    # ------------------------
    # Target Handling
    # ------------------------
    def handle_target_arg(self, target_arg, targets_file):
        if Path(target_arg).exists():
            new_targets = Path(target_arg).read_text().strip().splitlines()
        else:
            new_targets = [target_arg]

        if targets_file.exists():
            existing_targets = targets_file.read_text().splitlines()
            if not all(target in existing_targets for target in new_targets):
                action = Prompt.ask(
                    "Targets differ. Choose action",
                    choices=["Overwrite", "Merge", "Skip", "Abort"],
                    default="Abort"
                )
                if action == "Overwrite":
                    targets_file.write_text("\n".join(new_targets))
                    (self.project_path / ".new_targets").touch()
                    self.info("Targets overwritten.")
                elif action == "Merge":
                    merged = sorted(set(existing_targets + new_targets))
                    targets_file.write_text("\n".join(merged))
                    (self.project_path / ".new_targets").touch()
                    self.info("Targets merged.")
                elif action == "Skip":
                    self.info("Target update skipped.")
                    return
                else:
                    self.critical("Aborting due to target mismatch.")
        else:
            targets_file.write_text("\n".join(new_targets))
            self.info("New targets file created.")

    # ------------------------
    # Project Logic
    # ------------------------
    def initialize_new_project(self):
        self.info(f"Initializing new pentest project at {self.project_path}")
        (self.project_path / "scope").mkdir(exist_ok=True)
        (self.project_path / "recon").mkdir(exist_ok=True)
        (self.project_path / "recon" / "hosts").mkdir(exist_ok=True)

        internal_ip = get_internal_ip()
        external_ip = get_external_ip()
        self.info(f"[yellow]Detected Internal IP:[/] {internal_ip}")
        self.info(f"[yellow]Detected External IP:[/] {external_ip}")

        if not Confirm.ask("Are these IP addresses correct?"):
            self.critical("IP addresses not confirmed.")

        self.project_data = {"internal_ip": internal_ip, "external_ip": external_ip}
        self.handle_config()
        self._setup_targets()
        self.save_project_data()

    def _setup_targets(self):
        scope_dir = self.project_path / "scope"
        targets_file = scope_dir / "targets.txt"
        #self.project_data["targets"] = targets_file

        if self.args.target:
            self.handle_target_arg(self.args.target, targets_file)
        else:
            existing_target = Path.cwd() / "targets.txt"
            if existing_target.exists():
                if Confirm.ask(f"Use {existing_target} as targets.txt?"):
                    shutil.copy(existing_target, targets_file)
                    self.info("Existing targets.txt copied to scope folder.")
                else:
                    self.critical("No target specified, exiting.")
            else:
                self.critical("No target specified and no targets.txt found.")

        self.project_data["targets_md5"] = md5_hash(targets_file)

    def save_project_data(self):
        with open(self.project_json, "w") as f:
            json.dump(self.project_data, f, indent=4)

    def load_existing_project(self):
        self.info("Existing project detected. Loading configuration.")
        with open(self.project_json, "r") as f:
            self.project_data = json.load(f)

        self.handle_config()
        self._verify_ip_addresses()
        self._verify_targets()
        self.save_project_data()

    def _verify_ip_addresses(self):
        if self.args.skip_ip_check:
            return

        current_internal = get_internal_ip()
        current_external = get_external_ip()
        if current_internal != self.project_data["internal_ip"] or current_external != self.project_data["external_ip"]:
            self.info(f"[red]IP address mismatch detected.[/]")
            if Confirm.ask("Update IP addresses?"):
                self.project_data["internal_ip"] = current_internal
                self.project_data["external_ip"] = current_external
                self.info("IP addresses updated.")
            else:
                self.critical("IP mismatch not confirmed. Exiting.")

    def _verify_targets(self):
        targets_file = self.project_path / "scope" / "targets.txt"
        if self.args.target:
            self.handle_target_arg(self.args.target, targets_file)
            self.project_data["targets_md5"] = md5_hash(targets_file)
        current_hash = md5_hash(targets_file)
        if current_hash != self.project_data["targets_md5"]:
            self.info("[red]Targets have changed![/]")
            if Confirm.ask("Confirm new targets?"):
                self.project_data["targets_md5"] = current_hash
                (self.project_path / ".new_targets").touch()
                self.info("New targets confirmed and flagged for re-run.")
            else:
                self.critical("Target change not confirmed. Exiting.")

    def run(self):
        self._ensure_directories()
        self._check_tmux()
        if not self.project_json.exists():
            self.initialize_new_project()
        else:
            self.load_existing_project()
        self.info(f"[green]Project [yellow]{self.project_path.name}[/] initialized successfully![/]")
        self.run_recon_phase()

    def run_recon_phase(self):
        # Placeholder for running the recon phase 1
        self.info("Starting Recon Phase...")
        recon = Recon(self.project_path,hosts_override=self.args.hosts)
        recon.run()
        self._phase_done(1)
