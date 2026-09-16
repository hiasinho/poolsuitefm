import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("quickshell"), "Quickshell is required for service integration tests")
class ServiceTest(unittest.TestCase):
    def run_shell_test(self, shell):
        with tempfile.TemporaryDirectory(prefix="poolsuite-service-test-") as directory:
            root = Path(directory)
            plugin = root / "plugin"
            plugin.mkdir()
            for filename in ("Service.qml", "Safety.js"):
                shutil.copyfile(ROOT / filename, plugin / filename)
            shutil.copyfile(ROOT / f"tests/{shell}", root / "shell.qml")
            environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", XDG_RUNTIME_DIR=directory,
                               XDG_CACHE_HOME=str(root / "cache"), XDG_STATE_HOME=str(root / "state"))
            environment.pop("WAYLAND_DISPLAY", None)
            result = subprocess.run(["quickshell", "-p", str(root / "shell.qml"), "--no-color"],
                                    capture_output=True, text=True, timeout=15, env=environment)
            return result, result.stdout + result.stderr

    def test_service_boundaries_and_stale_responses(self):
        result, output = self.run_shell_test("service.qml")
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("PASS: 35 service checks", output)
        self.assertNotIn("ERROR", output)

    def test_helper_launch_failure_is_surfaced(self):
        result, output = self.run_shell_test("process_failure.qml")
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("PASS: helper launch failure surfaced", output)


if __name__ == "__main__":
    unittest.main()
