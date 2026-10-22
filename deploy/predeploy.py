"""Run mandatory checks before migrations without platform shell parsing."""
import os
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

# Explicit owner-approved content activation, separate from normal code deployment.
editorial_version = os.environ.get("ANTHEEC_EDITORIAL_EDITION", "")
if editorial_version:
    if editorial_version not in {"ar-20261022-v1", "multilingual-20261022-v1"}:
        raise SystemExit("Unsupported editorial edition")
    subprocess.run([sys.executable, str(root / "manage.py"),
                    "publish_approved_editorial", "--apply"], cwd=root, check=True)

    if editorial_version == "multilingual-20261022-v1":
        subprocess.run([sys.executable, str(root / "manage.py"),
                        "publish_multilingual_editorial", "--apply"], cwd=root, check=True)
