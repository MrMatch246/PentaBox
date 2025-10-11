import subprocess
import pexpect
import re

class TmuxSession:
    def __init__(self, session_name: str):
        self.session_name = session_name
        self._seen_ips = set()      # IPs already returned
        self._printed_lines = set() # Lines already printed for debug
        self._partial = ""          # Partial line buffer
        # Check or create tmux session
        result = subprocess.run(
            ["tmux", "has-session", "-t", self.session_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            subprocess.run(["tmux", "new-session", "-d", "-s", self.session_name])

        self.child = pexpect.spawn(
            f"tmux attach-session -t {self.session_name}",
            encoding="utf-8",
            codec_errors="replace"
        )

    def send_line(self, line: str):
        subprocess.run(["tmux", "send-keys", "-t", self.session_name, line, "C-m"])

    def send_ctrl_c(self, count=1):
        for _ in range(count):
            subprocess.run(["tmux", "send-keys", "-t", self.session_name, "C-c"])

    def kill(self):
        self.send_ctrl_c(3)

    def interactive(self):
        self.child.interact()

    # --- Core robust line reader ---
    def recv_lines(self, timeout=0.2):
        """
        Reads available output from tmux and returns a list of **complete lines**.
        Partial lines are kept in a buffer for next call.
        """
        lines = []

        while True:
            try:
                chunk = self.child.read_nonblocking(size=4096, timeout=timeout)
                if not chunk:
                    break
                self._partial += chunk
                while "\n" in self._partial:
                    line, self._partial = self._partial.split("\n", 1)
                    line = line.rstrip("\r")
                    lines.append(line)
            except pexpect.TIMEOUT:
                break
            except pexpect.EOF:
                # Flush any remaining partial line
                if self._partial:
                    lines.append(self._partial)
                    self._partial = ""
                break

        return lines

    # --- Check finished scans and debug printing ---
    def check_finished_scans(self, timeout=0.2):
        """
        Returns a list of new IPs that have not been seen yet.
        Prints any line containing 'finished', 'scanning', or 'target' exactly once.
        """
        new_ips = []
        lines = self.recv_lines(timeout=timeout)

        for line in lines:
            # Extract IPs
            if "Finished scanning target" in line:
                ip = line.split("Finished scanning target")[1].split("in")[0].strip()
                if ip not in self._seen_ips:
                    self._seen_ips.add(ip)
                    new_ips.append(ip)
        return new_ips
