import QtQuick
import Quickshell.Io
import "Safety.js" as Safety

Item {
  id: root
  visible: false

  property var manifest: null
  readonly property string pluginDir: manifest && manifest.__sourceDir ? String(manifest.__sourceDir) : ""
  readonly property string helper: pluginDir + "/scripts/player.py"

  property bool running: false
  property bool playing: false
  property string station: "official"
  property string title: ""
  property string artist: ""
  property string artUrl: ""
  property string source: ""
  property string artRequestSource: ""
  property string pendingArtSource: ""
  property string activeAction: ""
  property int actionGeneration: 0
  property int statusGeneration: 0
  property int volume: 70
  property int position: 0
  property int duration: 0
  property bool shuffle: true
  readonly property bool busy: actionProcess.running

  function applySettings(value) {
    if (value && value.shuffle !== undefined) shuffle = value.shuffle === true
  }

  function refresh() {
    if (helper === "/scripts/player.py" || statusProcess.running || busy) return
    statusGeneration = actionGeneration
    statusProcess.command = [helper, "status"]
    statusProcess.running = true
  }

  function run(args) {
    if (helper === "/scripts/player.py" || busy) return
    actionGeneration += 1
    activeAction = String(args[0] || "")
    actionProcess.command = [helper].concat(args)
    actionProcess.running = true
  }

  function requestArtwork(value) {
    value = Safety.sourceUrl(value)
    if (!value) {
      artUrl = ""
      pendingArtSource = ""
      return
    }
    if (helper === "/scripts/player.py") return
    if (artProcess.running) {
      pendingArtSource = value
      return
    }
    artRequestSource = value
    artProcess.command = [helper, "artwork", value]
    artProcess.running = true
  }

  function applyArtwork(text) {
    var data = Safety.parseObject(text)
    if (!data) return
    var nextSource = Safety.sourceUrl(data.source)
    if (nextSource !== "" && nextSource === source && nextSource === artRequestSource)
      artUrl = Safety.artworkUrl(data.url)
  }

  function playStation(name) { run(["start", name, String(volume)].concat(shuffle ? ["--shuffle"] : [])) }
  function toggle() { running ? run(["toggle"]) : playStation(station) }
  function next() { if (running) run(["next"]) }
  function previous() { if (running) run(["previous"]) }
  function stop() { if (running) run(["stop"]) }
  function setVolume(value) {
    volume = Safety.boundedNumber(value, 100, volume)
    if (running) run(["volume", String(volume)])
  }

  function applyStatus(text) {
    if (statusGeneration !== actionGeneration) return
    var data = Safety.parseObject(text)
    if (!data || typeof data.running !== "boolean") data = { running: false }
    running = data.running === true
    playing = running && data.playing === true
    station = Safety.station(data.station, station)
    title = running ? Safety.displayText(data.title) : ""
    artist = running ? Safety.displayText(data.artist) : ""
    if (running) volume = Safety.boundedNumber(data.volume, 100, volume)
    position = running ? Safety.boundedNumber(data.position, Safety.timeLimit) : 0
    duration = running ? Safety.boundedNumber(data.duration, Safety.timeLimit) : 0

    var nextSource = running ? Safety.sourceUrl(data.source) : ""
    if (nextSource !== source) {
      source = nextSource
      artUrl = ""
      requestArtwork(source)
    }
  }

  Timer {
    interval: 1500
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  Timer {
    id: settleTimer
    interval: 500
    repeat: false
    onTriggered: root.refresh()
  }

  Process {
    id: statusProcess
    // The helper caps the complete ASCII JSON document at 16 KiB before writing.
    stdout: StdioCollector {
      id: statusOutput
      waitForEnd: true
      onStreamFinished: root.applyStatus(text)
    }
  }

  Process {
    id: actionProcess
    onExited: function(exitCode) {
      var completedAction = root.activeAction
      root.activeAction = ""
      if (exitCode === 0 && completedAction === "start") root.running = true
      if (exitCode === 0 && completedAction === "stop") {
        root.running = false
        root.playing = false
      }
      settleTimer.restart()
    }
  }

  Process {
    id: artProcess
    // Both source and URL are bounded by the helper before collection.
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyArtwork(text)
    }
    onExited: {
      var next = root.pendingArtSource
      root.pendingArtSource = ""
      if (next !== "" && next !== root.artRequestSource) root.requestArtwork(next)
    }
  }
}
