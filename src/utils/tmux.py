import subprocess
import pexpect

class TmuxSession:
    def __init__(self, session_name: str):
        self.session_name = session_name

        # Check if session exists
        result = subprocess.run(
            ["tmux", "has-session", "-t", self.session_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode != 0:
            # Create session if it doesn't exist
            subprocess.run(["tmux", "new-session", "-d", "-s", self.session_name])

        # Start an interactive tmux attach using pexpect
        self.child = pexpect.spawn(f"tmux attach-session -t {self.session_name}", encoding="utf-8")

    def send_line(self, line: str):
        """Send a command line into the tmux session."""
        subprocess.run(["tmux", "send-keys", "-t", self.session_name, line, "C-m"])

    def recv_line(self, timeout=5):
        """Receive a single line from the tmux session."""
        try:
            self.child.expect("\r\n", timeout=timeout)
            return self.child.before.strip()
        except pexpect.TIMEOUT:
            return None

    def recv_until(self, pattern: str, timeout=10):
        """Receive output from tmux until the given pattern is matched."""
        try:
            self.child.expect(pattern, timeout=timeout)
            return self.child.before + self.child.after
        except pexpect.TIMEOUT:
            return None

    def kill(self):
        self.send_ctrl_c(3)

    def interactive(self):
        """Switch to fully interactive mode with the tmux session."""
        self.child.interact()

    def send_ctrl_c(self, count=1):
        """Send Ctrl-C multiple times to the session."""
        for _ in range(count):
            subprocess.run(["tmux", "send-keys", "-t", self.session_name, "C-c"])
