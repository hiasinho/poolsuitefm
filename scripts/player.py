#!/usr/bin/env python3
"""Small mpv JSON-IPC controller for Poolsuite FM."""

import json
import os
import socket
import subprocess
import sys
import time
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

runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/poolsuitefm-{os.getuid()}"))
runtime.mkdir(parents=True, exist_ok=True)
sock_path = runtime / "poolsuitefm.sock"
station_path = runtime / "poolsuitefm.station"
art_path = runtime / "poolsuitefm.art.json"


def send(commands, timeout=1.0):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    client.connect(str(sock_path))
    for request_id, command in enumerate(commands, 1):
        payload = {"command": command, "request_id": request_id}
        client.sendall((json.dumps(payload) + "\n").encode())

    responses = {}
    buffer = b""
    while len(responses) < len(commands):
        chunk = client.recv(65536)
        if not chunk:
            break
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if not line:
                continue
            reply = json.loads(line)
            request_id = reply.get("request_id")
            if request_id:
                responses[request_id] = reply
    client.close()
    return [responses.get(i, {}) for i in range(1, len(commands) + 1)]


def stop():
    try:
        send([["quit"]])
    except (OSError, TimeoutError):
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
            except (OSError, TimeoutError):
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


def artwork_url(source):
    if not source or not source.startswith(("https://soundcloud.com/", "https://api-v2.soundcloud.com/")):
        return ""

    try:
        cached = json.loads(art_path.read_text())
    except (OSError, json.JSONDecodeError):
        cached = {}

    if source in cached:
        return cached[source]

    try:
        result = subprocess.run(
            ["yt-dlp", "--no-warnings", "--no-playlist", "--print", "%(thumbnail)s", source],
            capture_output=True, text=True, timeout=10,
        )
        url = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
    except (OSError, subprocess.TimeoutExpired):
        url = ""

    if url:
        cached[source] = url
        art_path.write_text(json.dumps(cached))
    return url


def status():
    properties = ["pause", "media-title", "metadata", "volume", "time-pos", "duration", "path"]
    try:
        replies = send([["get_property", name] for name in properties])
        values = {
            name: reply.get("data") if reply.get("error") == "success" else None
            for name, reply in zip(properties, replies)
        }
    except (OSError, TimeoutError, json.JSONDecodeError):
        print(json.dumps({"running": False, "station": read_station()}))
        return

    metadata = values.get("metadata") or {}
    title = metadata.get("title") or metadata.get("Title") or metadata.get("TITLE") or values.get("media-title") or ""
    artist = metadata.get("artist") or metadata.get("Artist") or metadata.get("ARTIST") or metadata.get("uploader") or ""
    print(json.dumps({
        "running": True,
        "playing": not bool(values.get("pause")),
        "station": read_station(),
        "title": str(title),
        "artist": str(artist),
        "volume": round(float(values.get("volume") or 0)),
        "position": round(float(values.get("time-pos") or 0)),
        "duration": round(float(values.get("duration") or 0)),
        "source": str(values.get("path") or ""),
    }))


def read_station():
    try:
        return station_path.read_text().strip()
    except OSError:
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
        source = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps({"source": source, "url": artwork_url(source)}))
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
