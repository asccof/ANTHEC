import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet, InvalidToken

SPEC = importlib.util.spec_from_file_location("encrypt_backup", Path(__file__).resolve().parents[1] / "tools/encrypt_backup.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BackupTests(unittest.TestCase):
    def test_authenticated_roundtrip_private_permissions_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
                "ANTHEC_BACKUP_KEY": Fernet.generate_key().decode(),
                "ANTHEEC_DATA_KEY": Fernet.generate_key().decode()}):
            source, export, restored = (Path(folder) / n for n in ("source.dump", "export.fernet", "restored.dump"))
            source.write_bytes(b"synthetic-only-encrypted-database-export")
            MODULE.transform(source, export)
            self.assertNotIn(source.read_bytes(), export.read_bytes())
            self.assertEqual(export.stat().st_mode & 0o777, 0o600)
            MODULE.transform(export, restored, decrypt=True)
            self.assertEqual(source.read_bytes(), restored.read_bytes())
            with self.assertRaises(FileExistsError):
                MODULE.transform(source, export)
            os.environ["ANTHEC_BACKUP_KEY"] = Fernet.generate_key().decode()
            with self.assertRaises(InvalidToken):
                MODULE.transform(export, Path(folder) / "wrong.dump", decrypt=True)
            self.assertFalse((Path(folder) / "wrong.dump").exists())

    def test_missing_or_shared_key_and_oversize_export_fail(self):
        key = Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"ANTHEC_BACKUP_KEY": key, "ANTHEEC_DATA_KEY": key}):
            source, target = Path(folder) / "source", Path(folder) / "target"
            source.write_bytes(b"synthetic")
            with self.assertRaises(ValueError):
                MODULE.transform(source, target)
            # Fernet accepts base64 whitespace; differing text must not permit
            # the same underlying encryption key to be reused.
            os.environ["ANTHEC_BACKUP_KEY"] = key + "\n"
            with self.assertRaises(ValueError):
                MODULE.transform(source, target)
            os.environ["ANTHEC_BACKUP_KEY"] = ""
            with self.assertRaises(ValueError):
                MODULE.transform(source, target)
            os.environ["ANTHEC_BACKUP_KEY"] = Fernet.generate_key().decode()
            os.environ["ANTHEEC_DATA_KEY"] = ""
            with self.assertRaises(ValueError):
                MODULE.transform(source, target)
            os.environ["ANTHEEC_DATA_KEY"] = "invalid"
            with self.assertRaises(ValueError):
                MODULE.transform(source, target)
            os.environ["ANTHEEC_DATA_KEY"] = key
            with patch.object(MODULE, "MAX_BYTES", 4), self.assertRaises(ValueError):
                MODULE.transform(source, target)
            self.assertFalse(target.exists())
