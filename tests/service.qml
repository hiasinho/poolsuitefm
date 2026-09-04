import QtQuick
import Quickshell
import "plugin" as Poolsuite

// test_service.py copies this into an isolated Quickshell configuration.
// No manifest is assigned, so the service cannot launch helpers or touch playback.
ShellRoot {
  id: root
  property int checks: 0
  readonly property string track: "https://soundcloud.com/artist/track"
  readonly property string image: "https://i1.sndcdn.com/artworks-example-original.jpg"

  Poolsuite.Service { id: player }

  function check(condition, message) {
    if (!condition) throw new Error(message)
    checks += 1
  }

  function status(values) {
    var data = { running: true, playing: true, station: "tokyo", title: "Title", artist: "Artist",
                 volume: 42, position: 10, duration: 120, source: track }
    if (values) for (var key in values) data[key] = values[key]
    player.applyStatus(JSON.stringify(data))
  }

  function runTests() {
    status()
    check(player.running && player.playing, "valid playback state")
    check(player.title === "Title" && player.artist === "Artist", "valid metadata")
    check(player.source === track && player.station === "tokyo", "valid source and station")
    check(player.volume === 42 && player.position === 10 && player.duration === 120, "valid numbers")

    status({ title: "<b>Title</b>\n\u202e end", artist: "x".repeat(1000), volume: "100", position: -1, duration: 1e20 })
    check(player.title === "<b>Title</b> end" && player.artist.length === 256, "bounded display text")
    check(player.volume === 42 && player.position === 0 && player.duration === 604800, "bounded typed numbers")
    status({ title: { bad: true }, artist: ["bad"], station: "unknown", source: "file:///tmp/track" })
    check(player.title === "" && player.artist === "" && player.station === "tokyo", "invalid metadata types")
    check(player.source === "" && player.artUrl === "", "invalid source")

    status()
    player.artRequestSource = track
    player.applyArtwork(JSON.stringify({ source: track, url: image }))
    check(player.artUrl === image, "valid artwork response")
    player.applyArtwork(JSON.stringify({ source: track, url: "file:///tmp/image.png" }))
    check(player.artUrl === "", "invalid artwork URL")
    player.applyArtwork(JSON.stringify({ source: track, url: image }))
    status({ source: track + "2" })
    check(player.artUrl === "", "track change clears artwork")
    player.applyArtwork(JSON.stringify({ source: track, url: image }))
    check(player.artUrl === "", "late artwork cannot cross tracks")
    player.applyArtwork(JSON.stringify({ source: track + "2", url: image }))
    check(player.artUrl === "", "artwork must match requested source too")
    player.artRequestSource = track + "2"
    player.applyArtwork(JSON.stringify({ source: track + "2", url: image }))
    check(player.artUrl === image, "current request can apply artwork")

    player.actionGeneration = 1
    status({ title: "Obsolete status", source: track })
    check(player.source === track + "2" && player.title === "Title", "obsolete status generation ignored")
    player.statusGeneration = 1
    status({ running: false })
    check(!player.running && !player.playing && player.title === "" && player.artist === "", "stopped status clears metadata")
    check(player.source === "" && player.artUrl === "" && player.volume === 42, "stopped status clears artwork and preserves volume")

    var invalid = ["broken", "[]", "null", "{}", '{"running":"yes"}', " ".repeat(16385)]
    for (var i = 0; i < invalid.length; i++) {
      status()
      player.artRequestSource = track
      player.artUrl = image
      player.pendingArtSource = track + "2"
      player.applyStatus(invalid[i])
      check(!player.running && !player.playing && player.title === "" && player.artist === "", "invalid status clears metadata")
      check(player.source === "" && player.artUrl === "" && player.pendingArtSource === "", "invalid status clears artwork queue")
    }
  }

  Component.onCompleted: {
    try {
      runTests()
      console.log("PASS: " + checks + " service checks")
      Qt.callLater(Qt.quit)
    } catch (error) {
      console.error("FAIL: " + error)
      Qt.callLater(function() { Qt.exit(1) })
    }
  }
}
