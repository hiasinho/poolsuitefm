import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("widget_ytdlp", ROOT / "scripts/widget_ytdlp.py")
widget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(widget)
URL = "https://soundcloud.com/poolsuite/sets/indie-summer"


class WidgetTest(unittest.TestCase):
    def test_normal_success_does_not_fetch_widget(self):
        with patch.object(widget, "run", return_value=(0, b"playlist", b"")) as run, \
                patch.object(widget.sys, "stdout", SimpleNamespace(buffer=io.BytesIO())) as stdout:
            self.assertEqual(widget.main([URL]), 0)
            self.assertEqual(stdout.buffer.getvalue(), b"playlist")
            self.assertEqual(run.call_count, 1)

    def test_retry_only_on_soundcloud_401_and_with_user_python(self):
        python = Path.home() / ".local/share/uv/tools/yt-dlp/bin/python"
        with patch.object(Path, "is_file", return_value=True), \
                patch.object(widget, "run", side_effect=[(1, b"partial", b"soundcloud HTTP 401"), (0, b"widget", b"")]) as run, \
                patch.object(widget.sys, "stdout", SimpleNamespace(buffer=io.BytesIO())) as stdout, \
                patch.object(widget.sys, "stderr", SimpleNamespace(write=lambda text: None, buffer=io.BytesIO())):
            self.assertEqual(widget.main([URL]), 0)
            self.assertEqual(stdout.buffer.getvalue(), b"widget")
        self.assertEqual(run.call_args_list[1].args[0][:3], [str(python), widget.__file__, "--widget"])
        for error in (b"soundcloud HTTP 403", b"other site HTTP 401"):
            with patch.object(widget, "run", return_value=(1, b"", error)) as run, \
                    patch.object(widget.sys, "stdout", SimpleNamespace(buffer=io.BytesIO())), \
                    patch.object(widget.sys, "stderr", SimpleNamespace(buffer=io.BytesIO())):
                self.assertEqual(widget.main([URL]), 1)
                run.assert_called_once()

    def test_missing_runtime_directory_fails_closed(self):
        environment = dict(os.environ)
        environment.pop("XDG_RUNTIME_DIR", None)
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(ValueError, "requires XDG_RUNTIME_DIR"):
                widget.widget_client_id()

    def test_assets_are_bounded_and_cache_is_validated(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"XDG_RUNTIME_DIR": directory}):
            asset = "https://widget.sndcdn.com/widget-9-abc.js"
            identifier = "a" * 32
            with patch.object(widget, "fetch", side_effect=[f'<script src="{asset}"></script>',
                                                           f'client_id:x?"{"b" * 32}":"{identifier}"']) as fetch:
                self.assertEqual(widget.widget_client_id(), identifier)
                self.assertEqual(fetch.call_count, 2)
            with patch.object(widget, "fetch") as fetch:
                self.assertEqual(widget.widget_client_id(), identifier)
                fetch.assert_not_called()
            (Path(directory) / "poolsuitefm.widget-client").write_text("bad")
            with patch.object(widget, "fetch", side_effect=["", ""]):
                with self.assertRaises(ValueError):
                    widget.widget_client_id()

    def test_child_output_and_time_are_bounded(self):
        with self.assertRaisesRegex(ValueError, "byte limit"):
            with patch.object(widget, "MAX_OUTPUT", 100):
                widget.run(["python3", "-c", "print('x' * 200)"], 2)
        with self.assertRaises(TimeoutError):
            widget.run(["python3", "-c", "import time; time.sleep(5)"], 0.1)


if __name__ == "__main__":
    unittest.main()
