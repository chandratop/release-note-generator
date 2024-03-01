import subprocess
from typing import Any
from types import SimpleNamespace

def run(cmd: str) -> SimpleNamespace:
    """
    Executes the command and returns boolean status and message
    """
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        return SimpleNamespace(fine=True, what=result.stdout)
    return SimpleNamespace(fine=False, what=result.stderr)
