"""Synthetic PostgreSQL export/envelope/restore drill; CI database only."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from cryptography.fernet import Fernet
from encrypt_backup import transform


def run(*args, env=None):
    subprocess.run(args, check=True, env=env, stdout=subprocess.DEVNULL)


def main():
    if os.environ.get("CI") != "true" or os.environ.get("PGDATABASE") != "antheec_test":
        raise SystemExit("Recovery drill is restricted to the synthetic CI database.")
    os.environ["ANTHEC_BACKUP_KEY"] = Fernet.generate_key().decode()
    restore = dict(os.environ, PGDATABASE="antheec_restore_test")
    with tempfile.TemporaryDirectory(prefix="anthec-synthetic-recovery-") as folder:
        proof = Path(folder) / 'proof.json'
        run(sys.executable, "manage.py", "shell", "-c",
            "import json; from pathlib import Path; from tools.recovery_fixture import seed,snapshot; "
            f"seed(); Path({str(proof)!r}).write_text(json.dumps(snapshot(), sort_keys=True))")
        plain, envelope, recovered = (Path(folder) / name for name in ("source.dump", "export.fernet", "restore.dump"))
        run("pg_dump", "--format=custom", "--no-owner", "--no-acl", "--file", str(plain))
        transform(plain, envelope)
        transform(envelope, recovered, decrypt=True)
        assert plain.read_bytes() == recovered.read_bytes()
        # A distinct database in the disposable CI PostgreSQL service. No
        # drop/clean command and no destructive in-place recovery.
        run("createdb", "antheec_restore_test")
        run("pg_restore", "--no-owner", "--no-acl", "--exit-on-error", "--dbname=antheec_restore_test", str(recovered))
        run(sys.executable, "manage.py", "shell", "-c",
            "import json; from pathlib import Path; from tools.recovery_fixture import snapshot; "
            f"assert json.loads(Path({str(proof)!r}).read_text()) == json.loads(json.dumps(snapshot()))", env=restore)
    print("PASS: synthetic PostgreSQL export, authenticated backup and isolated restore/decryption; "
          "all model counts/migrations, portrait, signature/stamp fixtures, six immutable PDFs, "
          "document credentials and encrypted audit match; incorrect data key rejected.")


if __name__ == "__main__":
    main()
