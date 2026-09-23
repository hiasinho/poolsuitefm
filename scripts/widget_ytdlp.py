#!/usr/bin/env python3
"""mpv yt-dlp adapter: retry SoundCloud 401s against the official widget API."""

import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

WIDGET_PAGE = "https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fccottrill%2Fsis"
WIDGET_API = "https://api-widget.soundcloud.com/"
ASSET = re.compile(r'https://widget\.sndcdn\.com/widget-[\w-]+\.js')
# The widget's unauthenticated client ID is the non-logged-in branch of its config.
CLIENT = re.compile(r'client_id\s*:\s*\w+\s*\?\s*"[A-Za-z0-9]{32}"\s*:\s*"([A-Za-z0-9]{32})"')
MAX_OUTPUT = 8 * 1024 * 1024
MAX_ERROR = 64 * 1024
CACHE_AGE = 60 * 60


def fetch(url, origin, limit):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=5) as response:
        # Never follow an asset redirect to an arbitrary origin.
        if not response.url.startswith(origin):
            raise ValueError("Widget asset redirected outside its origin")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Widget asset exceeds byte limit")
    return data.decode("utf-8")


def widget_client_id():
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        raise ValueError("Poolsuite FM requires XDG_RUNTIME_DIR; refusing to use a shared temporary directory")
    cache = Path(runtime_dir) / "poolsuitefm.widget-client"
    try:
        if time.time() - cache.stat().st_mtime < CACHE_AGE:
            with cache.open("rb") as cached:
                value = cached.read(33).decode("ascii")
            if re.fullmatch(r"[A-Za-z0-9]{32}", value):
                return value
    except (OSError, UnicodeError):
        pass
    page = fetch(WIDGET_PAGE, "https://w.soundcloud.com/", 64 * 1024)
    for asset in list(dict.fromkeys(ASSET.findall(page)))[-4:][::-1]:
        try:
            match = CLIENT.search(fetch(asset, "https://widget.sndcdn.com/", 3 * 1024 * 1024))
        except (OSError, ValueError, UnicodeError):
            continue
        if match:
            value = match.group(1)
            temporary = None
            try:
                cache.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=cache.parent, delete=False) as file:
                    temporary = Path(file.name)
                    file.write(value.encode("ascii"))
                os.replace(temporary, cache)
            except OSError:
                pass  # Cache is optional.
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            return value
    raise ValueError("Could not find widget client ID in official assets")


def widget_main(args):
    from yt_dlp import main
    from yt_dlp.extractor.soundcloud import SoundcloudBaseIE

    client_id = widget_client_id()
    SoundcloudBaseIE._API_V2_BASE = WIDGET_API

    def initialize(self):
        self._CLIENT_ID = client_id

    SoundcloudBaseIE._initialize_pre_login = initialize
    SoundcloudBaseIE._update_client_id = initialize
    main(args)


def run(command, timeout):
    # Spool instead of buffering a playlist in memory; publish stdout only on success.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=error)
        try:
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if output.tell() > MAX_OUTPUT or error.tell() > MAX_ERROR:
                    process.kill()
                    raise ValueError("yt-dlp output exceeds byte limit")
                if time.monotonic() >= deadline:
                    process.kill()
                    raise TimeoutError("yt-dlp extraction timed out")
                time.sleep(0.05)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
        output.seek(0, os.SEEK_END)
        error.seek(0, os.SEEK_END)
        if output.tell() > MAX_OUTPUT or error.tell() > MAX_ERROR:
            raise ValueError("yt-dlp output exceeds byte limit")
        output.seek(0)
        error.seek(0)
        return process.returncode, output.read(), error.read()


def main(args):
    user_tool = Path.home() / ".local/bin/yt-dlp"
    executable = str(user_tool) if os.access(user_tool, os.X_OK) else "yt-dlp"
    # Non-SoundCloud invocations (including --version) retain normal yt-dlp semantics.
    if not any(arg.startswith(("https://soundcloud.com/", "https://api-v2.soundcloud.com/")) for arg in args):
        return subprocess.call([executable, *args])
    try:
        code, output, error = run([executable, *args], 60)
        if code and b"401" in error and b"soundcloud" in error.lower():
            python = Path.home() / ".local/share/uv/tools/yt-dlp/bin/python"
            if python.is_file():
                sys.stderr.write("Poolsuite FM: SoundCloud 401; retrying with widget API\n")
                code, output, error = run([str(python), __file__, "--widget", *args], 60)
        sys.stdout.buffer.write(output)
        sys.stderr.buffer.write(error)
        return code
    except (OSError, ValueError, TimeoutError) as exc:
        print(f"Poolsuite FM: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if sys.argv[1:2] == ["--widget"]:
        widget_main(sys.argv[2:])
    else:
        sys.exit(main(sys.argv[1:]))
