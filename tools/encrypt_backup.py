"""Offline authenticated backup envelope. Never prints a key or database content.

Supply both ANTHEC_BACKUP_KEY and the original ANTHEEC_DATA_KEY privately from
the owner's secret manager so separation can be verified. Restore output must
stay on an encrypted private workstation.
This bounded, whole-file tool is for small owner-test exports, not large backups.
"""
import argparse
import base64
import hmac
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

MAX_BYTES = 128 * 1024 * 1024


def transform(source, target, *, decrypt=False):
    key = os.environ.get("ANTHEC_BACKUP_KEY", "")
    data_key = os.environ.get("ANTHEEC_DATA_KEY", "")
    if not key or not data_key or key == data_key:
        raise ValueError("A separate private backup key is required.")
    Fernet(data_key.encode())  # require a valid data key, not a dummy comparison
    cipher = Fernet(key.encode())
    if hmac.compare_digest(base64.urlsafe_b64decode(key.encode()),
                           base64.urlsafe_b64decode(data_key.encode())):
        raise ValueError("Backup and data keys must be cryptographically distinct.")
    source = Path(source)
    limit = MAX_BYTES * 2 if decrypt else MAX_BYTES
    with source.open("rb") as handle:
        payload = handle.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("Export exceeds this bounded owner-testing backup tool.")
    result = cipher.decrypt(payload) if decrypt else cipher.encrypt(payload)
    if decrypt and len(result) > MAX_BYTES:
        raise ValueError("Decrypted export exceeds the owner-testing size limit.")
    # Never overwrite an existing export/restore file, and never follow an
    # existing symlink. No plaintext temporary file is created by encryption.
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(result)
    except BaseException:
        Path(target).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["encrypt", "decrypt"])
    parser.add_argument("source")
    parser.add_argument("target")
    args = parser.parse_args()
    try:
        transform(args.source, args.target, decrypt=args.mode == "decrypt")
    except (OSError, ValueError, InvalidToken):
        parser.exit(1, "Backup operation failed; verify private key, integrity, size and output path.\n")
    print("Backup operation complete; keep exports and recovery keys private.")


if __name__ == "__main__":
    main()
