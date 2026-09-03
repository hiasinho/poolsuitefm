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
  property int volume: 70
  property int position: 0
  property int duration: 0
  property bool shuffle: true

  function applySettings(value) {
    if (value && value.shuffle !== undefined) shuffle = value.shuffle === true
  }

  function refresh() {
    if (helper === "/scripts/player.py" || statusProcess.running) return
    statusProcess.command = [helper, "status"]
    statusProcess.running = true
  }

  function run(args) {
    if (helper === "/scripts/player.py") return
    actionProcess.command = [helper].concat(args)
    actionProcess.running = true
  }

  function playStation(name) { run(["start", name].concat(shuffle ? ["--shuffle"] : [])) }
  function toggle() { running ? run(["toggle"]) : playStation(station) }
  function next() { if (running) run(["next"]) }
  function previous() { if (running) run(["previous"]) }
  function stop() { if (running) run(["stop"]) }
  function setVolume(value) { run(["volume", String(Math.round(value))]) }

  function applyStatus(text) {
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
    onExited: settleTimer.restart()
  }
}
