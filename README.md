# Poolsuite FM

A small, unofficial, browser-free Poolsuite player for the Omarchy bar.
It streams Poolsuite's public SoundCloud playlists through `mpv` and controls
playback from a native Quickshell panel.

## Requirements

- `mpv`
- `yt-dlp`

## Install

```bash
omarchy plugin add https://github.com/hiasinho/poolsuitefm --enable
```

During local development, link the repository into the plugin directory and
enable it:

```bash
ln -s ~/Work/poolsuitefm ~/.config/omarchy/plugins/io.github.hiasinho.poolsuitefm
omarchy plugin enable io.github.hiasinho.poolsuitefm --section center
```

## Controls

- Left click: open the player
- Right click: play/pause
- Middle click: next track
- Scroll: previous/next

All music is streamed from public playlists curated by Poolsuite. This project
is not affiliated with Poolsuite or SoundCloud.
