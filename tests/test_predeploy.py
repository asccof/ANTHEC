"""Exercise the pre-deploy entry point, including fail-before-migration."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PredeployTests(unittest.TestCase):
    def run_entrypoint(self, failure):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deploy").mkdir()
            script = root / "deploy" / "predeploy.py"
            script.write_text((Path(__file__).resolve().parents[1] /
                               "deploy" / "predeploy.py").read_text())
            (root / "manage.py").write_text(
                "import json, os, sys\n"
                "with open('calls.jsonl', 'a') as calls:\n"
                "    calls.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "if sys.argv[1] == 'check':\n"
                "    sys.exit(int(os.environ['SYNTHETIC_CHECK_EXIT']))\n")
            result = subprocess.run([sys.executable, str(script)],
                cwd=root.parent, env={**os.environ, "SYNTHETIC_CHECK_EXIT": str(failure)},
                capture_output=True, timeout=20)
            calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]
            return result.returncode, calls

    def test_separate_arguments_order_and_project_working_directory(self):
        code, calls = self.run_entrypoint(0)
        self.assertEqual(code, 0)
        self.assertEqual(calls, [["check", "--deploy", "--fail-level", "ERROR"],
                                 ["migrate", "--noinput"]])

    def test_failed_deployment_check_never_runs_migrations(self):
        code, calls = self.run_entrypoint(3)
        self.assertNotEqual(code, 0)
        self.assertEqual(calls, [["check", "--deploy", "--fail-level", "ERROR"]])
