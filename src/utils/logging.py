import logging
from logging import Formatter
from rich.console import Console
from rich.logging import RichHandler
from datetime import datetime
from pathlib import Path

class ConvenientLogging:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.log_dir = self.project_path / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file_handle = None
        self.console = None

    def getLogger(self, name , level=logging.INFO):
        log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        self.log_file_handle = open(log_file, "w", encoding="utf-8")

        self.console = Console()
        file_console = Console(file=self.log_file_handle)

        rh = RichHandler(console=self.console, rich_tracebacks=True, markup=True)
        fh = RichHandler(console=file_console, markup=True)
        for h in (rh, fh): h.setFormatter(Formatter("%(message)s"))

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers.clear()
        logger.addHandler(rh)
        logger.addHandler(fh)
        return logger

    def __del__(self):
        if self.log_file_handle and not self.log_file_handle.closed:
            self.log_file_handle.close()


# Example usage:
if __name__ == "__main__":
    from time import sleep
    log = ConvenientLogging(Path("")).getLogger(name="example_phase")
    for i in range(5):
        log.info(f"Logging message {i}")
        sleep(0.2)
