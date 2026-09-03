# Poolsuite FM

> Leisure-Enhancing Radio for the Omarchy Desktop

_From the “Unofficial but Highly Relaxed” Software Offices of the Internet_

Poolsuite FM places an infinity pool of summer sounds directly inside your
Omarchy bar. No browser windows. No tabs. No dress code. Simply select a
channel, lower your chair into the preferred reclining position, and allow
`mpv` to handle the rest.

## Where Leisure Meets Playback

This compact broadcasting instrument pairs Poolsuite’s public SoundCloud
playlists with a native Quickshell panel. Track details, original cover art,
channel selection, volume, and transport controls remain tastefully concealed
behind one small palm tree.

Eight professionally leisure-oriented departments are available:

- Official
- Official II
- Mixtapes
- Balearic Sundown
- Indie Summer
- Tokyo Disco
- Friday Nite Heat
- Hangover Club

## Required Pool Equipment

- [Omarchy](https://omarchy.org/)
- `mpv`
- `yt-dlp`

No browser is required or quietly opened behind your cabana.

## Installation

```bash
omarchy plugin add https://github.com/hiasinho/poolsuitefm --enable
```

## Configure Your Cabana

Poolsuite FM checks you into the right side of the bar by default. Relocate
the listening lounge whenever the view calls for it:

```bash
omarchy bar move io.github.hiasinho.poolsuitefm --section right
```

Shuffle is available in the plugin settings and enabled by default.

## Operating Instructions

- **Left click:** enter the listening lounge
- **Right click:** play or pause
- **Middle click:** advance to the next selection
- **Scroll:** move through the playlist

Inside the lounge you may select a channel, inspect the current record sleeve,
or conclude the broadcast entirely.

## The Leisure-Enhancing Approach

Playback runs invisibly through `mpv`. The helper communicates with it over a
local JSON IPC socket, while `yt-dlp` resolves SoundCloud audio and retrieves
cover art once per track. Artwork is cached so repeat visits remain pleasantly
unhurried.

## Important Resort Information

Poolsuite FM is an independent, unofficial player. It is not affiliated with
Poolsuite or SoundCloud. Music is streamed from public playlists curated by
Poolsuite; availability remains subject to the gracious hospitality of those
services.

## Check Out

When the season ends, return your room key at the front desk:

```bash
omarchy plugin remove io.github.hiasinho.poolsuitefm
```

_For true connoisseurs of desktop leisure._
