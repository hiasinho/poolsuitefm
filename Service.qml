import QtQuick
import Quickshell.Io

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
    if (!value) {
      artUrl = ""
      pendingArtSource = ""
      return
    }
    if (artProcess.running) {
      pendingArtSource = value
      return
    }
    artRequestSource = value
    artProcess.command = [helper, "artwork", value]
    artProcess.running = true
  }

  function applyArtwork(text) {
    try {
      var data = JSON.parse(String(text || "{}"))
      if (source === String(data.source || "")) artUrl = String(data.url || "")
    } catch (error) {}
  }

  function playStation(name) { run(["start", name, String(volume)].concat(shuffle ? ["--shuffle"] : [])) }
  function toggle() { running ? run(["toggle"]) : playStation(station) }
  function next() { if (running) run(["next"]) }
  function previous() { if (running) run(["previous"]) }
  function stop() { if (running) run(["stop"]) }
  function setVolume(value) {
    volume = Math.round(value)
    if (running) run(["volume", String(volume)])
  }

  function applyStatus(text) {
    if (statusGeneration !== actionGeneration) return
    try {
      var data = JSON.parse(String(text || "{}"))
      running = data.running === true
      playing = data.playing === true
      station = String(data.station || station)
      title = String(data.title || "")
      artist = String(data.artist || "")
      volume = Number(data.volume === undefined ? volume : data.volume)
      position = Number(data.position || 0)
      duration = Number(data.duration || 0)

      var nextSource = String(data.source || "")
      if (nextSource !== source) {
        source = nextSource
        artUrl = ""
        requestArtwork(source)
      }
    } catch (error) {
      running = false
      playing = false
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
