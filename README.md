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
channel selection, and transport controls remain tastefully concealed
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
- Python 3 (included with Omarchy)

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

## Data Boundaries

Track metadata and artwork references are untrusted, even when received over
mpv's local socket. The plugin applies these limits before handing data to QML:

- **mpv IPC:** at most 64 KiB per JSON line and 256 KiB per exchange, checked
  before parsing. Each exchange has an overall deadline (normally one second;
  startup probes use 100 ms). Oversized, malformed, or incomplete replies are
  rejected and sockets are closed.
- **Status:** only the documented playback fields are emitted. Title and artist
  are capped at 256 characters, made single-line, and stripped of control and
  display-formatting characters. Numbers must be finite; volume is clamped to
  0–100 and position/duration to 0–604800 seconds (seven days). Station keys are
  allowlisted. Every helper JSON document, including artwork replies, is capped
  at 16 KiB of ASCII-encoded JSON before stdout is written/collected.
- **Display:** plugin-owned labels explicitly use plain text. Shared tooltip
  text is sanitized, capped at 512 characters, and has markup delimiters replaced
  with inert lookalikes. QML also checks types, lengths, and URL policies before
  assigning service properties.
- **Source URLs:** only ASCII HTTPS URLs on exactly `soundcloud.com` or
  `api-v2.soundcloud.com` are accepted, with a maximum length of 2048 characters.
- **Artwork URLs:** only ASCII HTTPS URLs on exactly `i1.sndcdn.com` or
  `a1.sndcdn.com`, with a `.jpg`, `.jpeg`, `.png`, or `.webp` path, are accepted.
  The same 2048-character limit applies. Query strings are allowed; credentials,
  explicit ports, fragments, whitespace, backslashes, malformed percent escapes,
  and percent-encoded ASCII controls/backslashes are not allowed in either URL
  policy. These rules apply to fresh lookups, cached values, and QML assignment.
- **Artwork lookup:** the metadata-only `yt-dlp` invocation ignores user config,
  has a ten-second overall deadline, and reads at most 4 KiB of stdout before
  rejecting overflow. Stderr is discarded. Only a successful process with one
  nonempty, policy-compliant thumbnail line is accepted.
- **Artwork cache:** `$XDG_RUNTIME_DIR/poolsuitefm.art.json` is read with a 256 KiB
  byte ceiling before JSON parsing. Only validated source/URL pairs are retained,
  with at most 128 entries and 256 KiB of serialized data. Least recently used
  entries are evicted as needed. Normalized contents are published using a
  temporary file and atomic replacement; corrupt or unwritable caches are
  optional failures, not playback requirements.

Rejected IPC replies produce an unavailable status; invalid metadata fields use
safe defaults, and rejected artwork uses the palm icon. The image-origin policy
covers URLs assigned to QML; Qt handles the actual image requests and redirects.
It is not a redirect-destination allowlist, an image transfer-size limit, or a
sandbox for mpv/yt-dlp.

## Development Checks

Run the Python tests, including isolated Quickshell service checks when
`quickshell` is installed:

```bash
python3 -m unittest discover -s tests -v
```

Run the Qt Quick safety tests with Qt 6's `qmltestrunner` (`qt6-declarative` on
Omarchy):

```bash
QT_QPA_PLATFORM=offscreen QML_XHR_ALLOW_FILE_READ=1 \
  /usr/lib/qt6/bin/qmltestrunner -input tests -o -,txt
```

These tests use temporary runtime/cache directories and controlled subprocesses.
They do not access the network or change your active player or desktop
configuration.

## Important Resort Information

Poolsuite FM is an independent, unofficial player. It is not affiliated with
Poolsuite or SoundCloud. Music is streamed from public playlists curated by
Poolsuite; availability remains subject to the gracious hospitality of those
services.

The palm-tree symbol is by [DarkEvil](https://commons.wikimedia.org/wiki/File:Palm_tree_symbol.svg)
and is in the public domain.

## Check Out

When the season ends, return your room key at the front desk:

```bash
omarchy plugin remove io.github.hiasinho.poolsuitefm
```

_For true connoisseurs of desktop leisure._
