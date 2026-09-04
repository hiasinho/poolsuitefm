#!/usr/bin/env python3
"""Small mpv JSON-IPC controller for Poolsuite FM."""

import json
import math
import os
import re
import selectors
import socket
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

PLAYLISTS = {
    "official": "https://soundcloud.com/poolsuite/sets/poolsuite-fm-official-playlist",
    "official2": "https://soundcloud.com/poolsuite/sets/poolsuite-fm-official-playlist-two",
    "mixtapes": "https://soundcloud.com/poolsuite/sets/poolsuite-mixtapes",
    "balearic": "https://soundcloud.com/poolsuite/sets/balearic-sundown",
    "indie": "https://soundcloud.com/poolsuite/sets/indie-summer",
    "tokyo": "https://soundcloud.com/poolsuite/sets/tokyo-disco",
    "friday": "https://soundcloud.com/poolsuite/sets/friday-nite-heat",
    "hangover": "https://soundcloud.com/poolsuite/sets/hangover-club",
}

MAX_IPC_LINE_BYTES = 64 * 1024
MAX_IPC_TOTAL_BYTES = 256 * 1024
MAX_TEXT_CHARS = 256
MAX_URL_CHARS = 2048
MAX_TIME_SECONDS = 7 * 24 * 60 * 60
MAX_HELPER_OUTPUT_BYTES = 16 * 1024
MAX_THUMBNAIL_OUTPUT_BYTES = 4 * 1024
MAX_CACHE_BYTES = 256 * 1024
MAX_CACHE_ENTRIES = 128
ARTWORK_TIMEOUT = 10

# Keep these URL policies and display limits in sync with Safety.js.
URL_PATH = r"[A-Za-z0-9._~!$&'()*+,;=:@%/-]+"
URL_QUERY = r"(?:\?[A-Za-z0-9._~!$&'()*+,;=:@%/?-]*)?"
SOURCE_URL = re.compile(r"https://(?:soundcloud\.com|api-v2\.soundcloud\.com)/" + URL_PATH + URL_QUERY)
ARTWORK_URL = re.compile(r"https://(?:i1|a1)\.sndcdn\.com/" + URL_PATH + r"\.(?:jpg|jpeg|png|webp)" + URL_QUERY)
UNSAFE_ESCAPE = re.compile(r"%(?![0-9a-f]{2})|%(?:0[0-9a-f]|1[0-9a-f]|7f|5c)", re.IGNORECASE)

runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/poolsuitefm-{os.getuid()}"))
runtime.mkdir(parents=True, exist_ok=True)
sock_path = runtime / "poolsuitefm.sock"
station_path = runtime / "poolsuitefm.station"
art_path = runtime / "poolsuitefm.art.json"


def remaining_time(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Player response deadline exceeded")
    return remaining


def send(commands, timeout=1.0):
    deadline = time.monotonic() + timeout
    responses = {}
    buffer = b""
    received = 0
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(remaining_time(deadline))
        client.connect(str(sock_path))
        for request_id, command in enumerate(commands, 1):
            payload = {"command": command, "request_id": request_id}
            client.settimeout(remaining_time(deadline))
            client.sendall((json.dumps(payload) + "\n").encode())

        while len(responses) < len(commands):
            client.settimeout(remaining_time(deadline))
            chunk = client.recv(min(8192, MAX_IPC_TOTAL_BYTES - received + 1,
                                    MAX_IPC_LINE_BYTES - len(buffer) + 1))
            if not chunk:
                raise ValueError("Incomplete mpv response")
            received += len(chunk)
            if received > MAX_IPC_TOTAL_BYTES:
                raise ValueError("mpv response exceeds byte limit")
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if len(line) > MAX_IPC_LINE_BYTES:
                    raise ValueError("mpv response line exceeds byte limit")
                if not line:
                    continue
                reply = json.loads(line)
                if not isinstance(reply, dict):
                    raise ValueError("Invalid mpv response object")
                request_id = reply.get("request_id")
                # Events, unknown IDs and duplicates cannot complete a request.
                if type(request_id) is int and 1 <= request_id <= len(commands):
                    responses.setdefault(request_id, reply)
            if len(buffer) > MAX_IPC_LINE_BYTES:
                raise ValueError("mpv response line exceeds byte limit")
    return [responses[i] for i in range(1, len(commands) + 1)]


def stop():
    try:
        send([["quit"]])
    except (OSError, ValueError, RecursionError):
        pass
    for _ in range(20):
        if not sock_path.exists():
            return
        time.sleep(0.05)
    sock_path.unlink(missing_ok=True)


def start(station, volume, shuffle):
    if station not in PLAYLISTS:
        raise SystemExit(f"Unknown station: {station}")
    stop()
    command = [
        "mpv", "--no-video", "--really-quiet", "--force-window=no",
        f"--input-ipc-server={sock_path}", f"--volume={max(0, min(100, volume))}",
    ]
    if shuffle:
        command.append("--shuffle")
    command.append(PLAYLISTS[station])
    with open(os.devnull, "rb") as stdin, open(os.devnull, "ab") as output:
        player = subprocess.Popen(
            command, stdin=stdin, stdout=output, stderr=output,
            start_new_session=True, close_fds=True,
        )
    try:
        ready = False
        for _ in range(100):
            try:
                replies = send([["get_property", "pause"]], timeout=0.1)
                if replies and replies[0].get("error") == "success":
                    ready = True
                    break
            except (OSError, ValueError, RecursionError):
                pass
            time.sleep(0.05)

        if not ready:
            raise RuntimeError("mpv did not open its IPC socket")
        station_path.write_text(station)
    except Exception as error:
        if player.poll() is None:
            player.terminate()
            try:
                player.wait(timeout=1)
            except subprocess.TimeoutExpired:
                player.kill()
        sock_path.unlink(missing_ok=True)
        raise SystemExit(str(error)) from error


def valid_url(value, pattern):
    if not isinstance(value, str) or len(value) > MAX_URL_CHARS:
        return ""
    return value if pattern.fullmatch(value) and not UNSAFE_ESCAPE.search(value) else ""


def source_url(value):
    return valid_url(value, SOURCE_URL)


def image_url(value):
    return valid_url(value, ARTWORK_URL)


def read_bounded(path, limit):
    with path.open("rb") as file:
        data = file.read(limit + 1)
    if len(data) > limit:
        raise ValueError("File exceeds byte limit")
    return data


def encode_json(data):
    return json.dumps(data, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("ascii")


def normalize_cache(data):
    cached = {}
    if isinstance(data, dict):
        for source, url in data.items():
            if source_url(source) and image_url(url):
                cached[source] = url
                if len(cached) > MAX_CACHE_ENTRIES:
                    del cached[next(iter(cached))]
    while len(encode_json(cached)) > MAX_CACHE_BYTES:
        del cached[next(iter(cached))]
    return cached


def read_art_cache():
    try:
        return normalize_cache(json.loads(read_bounded(art_path, MAX_CACHE_BYTES)))
    except (OSError, ValueError, RecursionError):
        return {}


def write_art_cache(cached):
    temporary = None
    try:
        data = encode_json(normalize_cache(cached))
        with tempfile.NamedTemporaryFile(mode="wb", dir=art_path.parent,
                                         prefix=art_path.name + ".", delete=False) as file:
            temporary = Path(file.name)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, art_path)
    except OSError:
        # Artwork caching is optional; playback must not depend on a writable cache.
        pass
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def thumbnail_output(source):
    command = [
        "yt-dlp", "--ignore-config", "--no-warnings", "--no-playlist",
        "--skip-download", "--print", "%(thumbnail)s", "--", source,
    ]
    deadline = time.monotonic() + ARTWORK_TIMEOUT
    with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL) as process:
        try:
            output = bytearray()
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    if not selector.select(remaining_time(deadline)):
                        raise TimeoutError("Artwork response deadline exceeded")
                    chunk = os.read(process.stdout.fileno(), min(4096, MAX_THUMBNAIL_OUTPUT_BYTES - len(output) + 1))
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > MAX_THUMBNAIL_OUTPUT_BYTES:
                        raise ValueError("Artwork response exceeds byte limit")
            if process.wait(timeout=remaining_time(deadline)) != 0:
                raise ValueError("Artwork lookup failed")
            return output.decode("utf-8")
        finally:
            if process.poll() is None:
                process.kill()


def artwork_url(source):
    source = source_url(source)
    if not source:
        return ""

    cached = read_art_cache()
    url = cached.pop(source, "")
    if not url:
        try:
            lines = [line.strip() for line in thumbnail_output(source).splitlines() if line.strip()]
            url = image_url(lines[0]) if len(lines) == 1 else ""
        except (OSError, ValueError, subprocess.TimeoutExpired):
            url = ""
    if url:
        # Refresh insertion order; normalization evicts least recently used entries.
        cached[source] = url
    write_art_cache(cached)
    return url


def display_text(value):
    if not isinstance(value, str):
        return ""
    characters = []
    for character in value[:MAX_TEXT_CHARS]:
        category = unicodedata.category(character)
        if category in ("Cc", "Zl", "Zp"):
            characters.append(" ")
        elif category not in ("Cf", "Cs"):
            characters.append(character)
    return " ".join("".join(characters).split())


def bounded_number(value, maximum, default=0):
    if type(value) not in (int, float) or (isinstance(value, float) and not math.isfinite(value)):
        return default
    return round(max(0, min(maximum, value)))


def emit_json(data):
    output = encode_json(data)
    if len(output) + 1 > MAX_HELPER_OUTPUT_BYTES:
        raise ValueError("Helper output exceeds byte limit")
    print(output.decode("ascii"))


def status():
    data = {
        "running": False, "playing": False, "station": read_station(),
        "title": "", "artist": "", "volume": 70, "position": 0, "duration": 0, "source": "",
    }
    properties = ["pause", "media-title", "metadata", "volume", "time-pos", "duration", "path"]
    try:
        replies = send([["get_property", name] for name in properties])
        values = {
            name: reply.get("data") if reply.get("error") == "success" else None
            for name, reply in zip(properties, replies)
        }
    except (OSError, ValueError, RecursionError):
        emit_json(data)
        return

    metadata = values.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    titles = [metadata.get(key) for key in ("title", "Title", "TITLE")] + [values.get("media-title")]
    artists = [metadata.get(key) for key in ("artist", "Artist", "ARTIST", "uploader")]
    data.update({
        "running": True,
        "playing": values.get("pause") is False,
        "title": next((text for value in titles if (text := display_text(value))), ""),
        "artist": next((text for value in artists if (text := display_text(value))), ""),
        "volume": bounded_number(values.get("volume"), 100, 70),
        "position": bounded_number(values.get("time-pos"), MAX_TIME_SECONDS),
        "duration": bounded_number(values.get("duration"), MAX_TIME_SECONDS),
        "source": source_url(values.get("path")),
    })
    emit_json(data)


def read_station():
    try:
        station = read_bounded(station_path, 64).decode("utf-8").strip()
        return station if station in PLAYLISTS else "official"
    except (OSError, ValueError):
        return "official"


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "start":
        station = sys.argv[2] if len(sys.argv) > 2 else "official"
        volume = int(sys.argv[3]) if len(sys.argv) > 3 else 70
        start(station, volume, "--shuffle" in sys.argv[4:])
    elif action == "status":
        status()
    elif action == "artwork":
        source = source_url(sys.argv[2]) if len(sys.argv) > 2 else ""
        emit_json({"source": source, "url": artwork_url(source)})
    elif action == "toggle":
        send([["cycle", "pause"]])
    elif action == "next":
        send([["playlist-next", "force"]])
    elif action == "previous":
        send([["playlist-prev", "force"]])
    elif action == "volume":
        send([["set_property", "volume", max(0, min(100, int(sys.argv[2])))]])
    elif action == "stop":
        stop()
        station_path.unlink(missing_ok=True)
    else:
        raise SystemExit(f"Unknown action: {action}")


if __name__ == "__main__":
    main()
