"""Run mandatory checks before migrations without platform shell parsing."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for arguments in (
    ["check", "--deploy", "--fail-level", "ERROR"],
    ["migrate", "--noinput"],
):
    subprocess.run([sys.executable, str(root / "manage.py"), *arguments],
                   cwd=root, check=True)
