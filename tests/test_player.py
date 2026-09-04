import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
# Import without touching the user's runtime directory or active player.
with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"XDG_RUNTIME_DIR": directory}):
    spec = importlib.util.spec_from_file_location("player", ROOT / "scripts/player.py")
    player = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(player)

SOURCE = "https://soundcloud.com/artist/track"
IMAGE = "https://i1.sndcdn.com/artworks-example-original.jpg"


class FakeSocket:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.closed = False
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def connect(self, path):
        pass

    def settimeout(self, timeout):
        pass

    def sendall(self, data):
        self.sent.append(json.loads(data))

    def recv(self, size):
        if not self.chunks:
            return b""
        data = self.chunks.pop(0)
        if len(data) > size:
            self.chunks.insert(0, data[size:])
        return data[:size]


def reply(request_id, data=None):
    return json.dumps({"request_id": request_id, "error": "success", "data": data}).encode() + b"\n"


class PlayerTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        runtime = patch.multiple(player, sock_path=self.directory / "player.sock",
                                 station_path=self.directory / "station", art_path=self.directory / "art.json")
        runtime.start()
        self.addCleanup(runtime.stop)

    def status(self, **overrides):
        values = {"pause": False, "media-title": "Fallback", "metadata": {}, "volume": 70,
                  "time-pos": 10, "duration": 120, "path": SOURCE}
        values.update(overrides)
        responses = [{"error": "success", "data": value} for value in values.values()]
        with patch.object(player, "send", return_value=responses), contextlib.redirect_stdout(io.StringIO()) as output:
            player.status()
        text = output.getvalue()
        self.assertLessEqual(len(text.encode()), player.MAX_HELPER_OUTPUT_BYTES)
        return json.loads(text)

    def test_ipc_fragmentation_events_duplicates_and_unknown_ids(self):
        data = b'{"event":"metadata-update"}\n' + reply(999) + reply(True) + reply(1.0)
        data += reply(2, "second") + reply(2, "duplicate") + reply(1, "first")
        client = FakeSocket([data[:17], data[17:93], data[93:]])
        with patch.object(player.socket, "socket", return_value=client):
            result = player.send([["first"], ["second"]])
        self.assertEqual([item["data"] for item in result], ["first", "second"])
        self.assertTrue(client.closed)
        self.assertEqual([item["request_id"] for item in client.sent], [1, 2])

    def test_ipc_line_limit_before_json_parsing(self):
        for suffix in (b"", b"\n"):
            with self.subTest(newline=bool(suffix)):
                client = FakeSocket([b"x" * (player.MAX_IPC_LINE_BYTES + 1) + suffix])
                with patch.object(player.socket, "socket", return_value=client), patch.object(player.json, "loads") as loads:
                    # FakeSocket.sendall normally parses outgoing commands too.
                    client.sendall = lambda data: None
                    with self.assertRaisesRegex(ValueError, "line exceeds"):
                        player.send([["test"]])
                    loads.assert_not_called()
                self.assertTrue(client.closed)

    def test_ipc_accepts_exact_line_and_total_limits(self):
        padding = player.MAX_IPC_LINE_BYTES - (len(reply(1, "")) - 1)
        data = reply(1, "x" * padding)
        client = FakeSocket([data])
        with patch.object(player.socket, "socket", return_value=client), \
                patch.object(player, "MAX_IPC_TOTAL_BYTES", len(data)):
            self.assertEqual(player.send([["test"]])[0]["data"], "x" * padding)
        self.assertTrue(client.closed)

    def test_ipc_total_limit_including_events(self):
        client = FakeSocket([b'{"event":"tick"}\n' * 100])
        with patch.object(player.socket, "socket", return_value=client), patch.object(player, "MAX_IPC_TOTAL_BYTES", 128):
            with self.assertRaisesRegex(ValueError, "byte limit"):
                player.send([["test"]])
        self.assertTrue(client.closed)

    def test_ipc_overall_deadline_stops_a_trickle(self):
        client = FakeSocket([b'{"event":"tick"}\n'] * 10)
        with patch.object(player.socket, "socket", return_value=client), \
                patch.object(player.time, "monotonic", side_effect=[0, 0, 0, 0.4, 0.8, 1.2]):
            with self.assertRaises(TimeoutError):
                player.send([["test"]], timeout=1)
        self.assertTrue(client.closed)

    def test_ipc_rejects_malformed_or_incomplete_replies(self):
        for data in (b"[]\n", b"null\n", b"false\n", b"invalid\n", b"\xff\n", b"", reply(999)):
            with self.subTest(data=data):
                client = FakeSocket([data])
                with patch.object(player.socket, "socket", return_value=client):
                    with self.assertRaises(ValueError):
                        player.send([["test"]])
                self.assertTrue(client.closed)

    def test_status_bounded_schema_and_display_controls(self):
        data = self.status(metadata={"title": "<b>Title</b>\x1b\n\u202e end", "artist": "🌴" * 1000,
                                     "unused": "x" * 100000}, **{"path": "x" * 100000})
        self.assertEqual(data["title"], "<b>Title</b> end")
        self.assertEqual(data["artist"], "🌴" * player.MAX_TEXT_CHARS)
        self.assertEqual(data["source"], "")
        self.assertEqual(set(data), {"running", "playing", "station", "title", "artist", "volume", "position", "duration", "source"})

    def test_status_wrong_metadata_types_and_tag_fallbacks(self):
        for metadata in (["unexpected"], "string", 123, True, None):
            with self.subTest(metadata=metadata):
                data = self.status(metadata=metadata)
                self.assertEqual(data["title"], "Fallback")
                self.assertEqual(data["artist"], "")
        data = self.status(metadata={"title": ["wrong"], "Title": "Uppercase", "artist": {}, "uploader": "Uploader"})
        self.assertEqual((data["title"], data["artist"]), ("Uppercase", "Uploader"))

    def test_status_finite_bounded_numbers_and_boolean_pause(self):
        for invalid in (float("inf"), float("-inf"), float("nan"), "100", {}, [], True):
            with self.subTest(value=invalid):
                data = self.status(volume=invalid, **{"time-pos": invalid, "duration": invalid, "pause": invalid})
                self.assertEqual((data["volume"], data["position"], data["duration"], data["playing"]), (70, 0, 0, False))
        data = self.status(volume=10**1000, **{"time-pos": -10, "duration": 10**1000})
        self.assertEqual((data["volume"], data["position"], data["duration"]), (100, 0, player.MAX_TIME_SECONDS))
        self.assertEqual(self.status(volume=42.2)["volume"], 42)

    def test_status_fallback_for_protocol_failures(self):
        for error in (OSError(), TimeoutError(), ValueError(), RecursionError()):
            with self.subTest(error=error), patch.object(player, "send", side_effect=error), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                player.status()
                data = json.loads(output.getvalue())
                self.assertFalse(data["running"])
                self.assertFalse(data["playing"])
                self.assertEqual((data["title"], data["source"]), ("", ""))

    def test_station_file_is_bounded_and_allowlisted(self):
        self.assertEqual(player.read_station(), "official")
        for contents in (b"x" * 65, b"unknown", b"\xff", b"<b>station</b>"):
            player.station_path.write_bytes(contents)
            self.assertEqual(player.read_station(), "official")
        player.station_path.write_text("tokyo\n")
        self.assertEqual(player.read_station(), "tokyo")

    def test_url_policies(self):
        for case in json.loads((ROOT / "tests/url_cases.json").read_text()):
            with self.subTest(case=case["tag"]):
                validate = player.source_url if case["kind"] == "source" else player.image_url
                self.assertEqual(validate(case["value"]), case["value"] if case["valid"] else "")

    def test_url_length_boundaries(self):
        for validate, prefix, suffix in ((player.source_url, "https://soundcloud.com/", ""),
                                         (player.image_url, "https://i1.sndcdn.com/", ".jpg")):
            url = prefix + "a" * (player.MAX_URL_CHARS - len(prefix) - len(suffix)) + suffix
            self.assertEqual(validate(url), url)
            self.assertEqual(validate(url.replace("/a", "/aa", 1)), "")

    def test_artwork_cli_does_not_echo_unbounded_or_invalid_source(self):
        with patch.object(player.sys, "argv", ["player.py", "artwork", "x" * 100000]), \
                patch.object(player, "thumbnail_output") as fetch, contextlib.redirect_stdout(io.StringIO()) as output:
            player.main()
        self.assertEqual(json.loads(output.getvalue()), {"source": "", "url": ""})
        fetch.assert_not_called()

    def test_emit_json_enforces_byte_ceiling(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(ValueError):
                player.emit_json({"title": "x" * player.MAX_HELPER_OUTPUT_BYTES})
        self.assertEqual(output.getvalue(), "")

    def test_cache_rejects_bad_shape_encoding_and_oversized_file(self):
        for data in (b"[]", b"null", b'"string"', b"{broken", b"\xff", b"[" * 2000,
                     b" " * (player.MAX_CACHE_BYTES + 1)):
            with self.subTest(data=data[:20]):
                player.art_path.write_bytes(data)
                self.assertEqual(player.read_art_cache(), {})

    def test_cache_read_is_bounded_before_parsing(self):
        class RecordingFile(io.BytesIO):
            def read(file, size=-1):
                self.assertEqual(size, player.MAX_CACHE_BYTES + 1)
                return super(RecordingFile, file).read(size)

        with patch.object(Path, "open", return_value=RecordingFile(b" " * (player.MAX_CACHE_BYTES + 1))), \
                patch.object(player.json, "loads") as loads:
            self.assertEqual(player.read_art_cache(), {})
            loads.assert_not_called()

    def test_cache_filters_keys_and_values(self):
        cache = {SOURCE: IMAGE, "file:///track": IMAGE, SOURCE + "2": "file:///tmp/image.png",
                 SOURCE + "3": {"url": IMAGE}, SOURCE + "x" * player.MAX_URL_CHARS: IMAGE}
        player.art_path.write_text(json.dumps(cache))
        self.assertEqual(player.read_art_cache(), {SOURCE: IMAGE})

    def test_cache_entry_and_serialized_byte_limits(self):
        cache = {SOURCE + str(i): IMAGE for i in range(player.MAX_CACHE_ENTRIES + 5)}
        normalized = player.normalize_cache(cache)
        self.assertEqual(len(normalized), player.MAX_CACHE_ENTRIES)
        self.assertNotIn(SOURCE + "0", normalized)
        self.assertIn(SOURCE + "132", normalized)
        large = {SOURCE + str(i) + "x" * 1900: IMAGE + "?q=" + "y" * 1900 for i in range(128)}
        player.write_art_cache(large)
        self.assertLessEqual(player.art_path.stat().st_size, player.MAX_CACHE_BYTES)
        self.assertGreater(len(player.read_art_cache()), 0)
        self.assertLess(len(player.read_art_cache()), 128)

    def test_cache_publication_is_atomic_and_normalized(self):
        player.art_path.write_text("old contents")
        replace = os.replace

        def check_replace(temporary, target):
            self.assertEqual(Path(temporary).parent, target.parent)
            self.assertEqual(target.read_text(), "old contents")
            self.assertEqual(json.loads(Path(temporary).read_text()), {SOURCE: IMAGE})
            replace(temporary, target)

        with patch.object(player.os, "replace", side_effect=check_replace) as publish:
            player.write_art_cache({SOURCE: IMAGE, "bad": "bad"})
        publish.assert_called_once()
        self.assertEqual(list(self.directory.iterdir()), [player.art_path])

    def test_cache_write_failure_preserves_old_file_and_artwork(self):
        player.art_path.write_text("{}")
        with patch.object(player.os, "replace", side_effect=PermissionError()), \
                patch.object(player, "thumbnail_output", return_value=IMAGE + "\n"):
            self.assertEqual(player.artwork_url(SOURCE), IMAGE)
        self.assertEqual(player.art_path.read_text(), "{}")
        self.assertEqual(list(self.directory.iterdir()), [player.art_path])

    def test_artwork_cache_hit_refreshes_recency_without_fetching(self):
        player.art_path.write_text(json.dumps({SOURCE: IMAGE, SOURCE + "2": IMAGE}))
        with patch.object(player, "thumbnail_output") as fetch:
            self.assertEqual(player.artwork_url(SOURCE), IMAGE)
        fetch.assert_not_called()
        self.assertEqual(list(player.read_art_cache()), [SOURCE + "2", SOURCE])

    def test_invalid_cached_artwork_is_never_returned(self):
        player.art_path.write_text(json.dumps({SOURCE: "file:///tmp/image.png"}))
        with patch.object(player, "thumbnail_output", side_effect=OSError()):
            self.assertEqual(player.artwork_url(SOURCE), "")
        self.assertEqual(json.loads(player.art_path.read_text()), {})

    def test_thumbnail_schema_validation_and_safe_failure(self):
        for output in ("file:///tmp/image.png\n", "NA\n", IMAGE + "\n" + IMAGE, IMAGE + "x" * 2048):
            with self.subTest(output=output[:60]), patch.object(player, "thumbnail_output", return_value=output):
                self.assertEqual(player.artwork_url(SOURCE), "")
        for error in (OSError(), TimeoutError(), ValueError(), subprocess.TimeoutExpired("yt-dlp", 10)):
            with self.subTest(error=error), patch.object(player, "thumbnail_output", side_effect=error):
                self.assertEqual(player.artwork_url(SOURCE), "")

    def run_thumbnail_child(self, code, expected_error=None):
        popen = subprocess.Popen
        children = []

        def spawn(command, **kwargs):
            self.assertEqual(command[0], "yt-dlp")
            self.assertIn("--ignore-config", command)
            self.assertIn("--skip-download", command)
            self.assertEqual(command[-2:], ["--", SOURCE])
            self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
            child = popen([sys.executable, "-c", code], **kwargs)
            children.append(child)
            return child

        with patch.object(player.subprocess, "Popen", side_effect=spawn), patch.object(player, "ARTWORK_TIMEOUT", 0.3):
            if expected_error:
                with self.assertRaises(expected_error):
                    player.thumbnail_output(SOURCE)
                result = None
            else:
                result = player.thumbnail_output(SOURCE)
        self.assertTrue(children)
        self.assertIsNotNone(children[0].poll(), "Child must be reaped even on timeout/overflow")
        return result

    def test_thumbnail_stdout_is_bounded_while_reading(self):
        self.run_thumbnail_child("import os, time; os.write(1, b'x' * 4097); time.sleep(5)", ValueError)

    def test_thumbnail_deadline_covers_silence_trickle_and_wait(self):
        self.run_thumbnail_child("import time; time.sleep(5)", TimeoutError)
        self.run_thumbnail_child("import os, time\nfor i in range(100):\n os.write(1, b'x'); time.sleep(0.03)", TimeoutError)
        self.run_thumbnail_child("import os, time; os.close(1); time.sleep(5)", subprocess.TimeoutExpired)

    def test_thumbnail_stderr_is_discarded_and_stdout_decoded(self):
        result = self.run_thumbnail_child(f"import os; os.write(2, b'x' * 1000000); print({IMAGE!r})")
        self.assertEqual(result, IMAGE + "\n")
        self.run_thumbnail_child("import os; os.write(1, b'\\xff')", UnicodeDecodeError)

    def test_thumbnail_nonzero_exit_rejects_even_valid_stdout(self):
        self.run_thumbnail_child(f"import sys; print({IMAGE!r}); sys.exit(1)", ValueError)


if __name__ == "__main__":
    unittest.main()
