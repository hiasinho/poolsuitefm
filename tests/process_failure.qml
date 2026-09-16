import QtQuick
import Quickshell
import "plugin" as Poolsuite

ShellRoot {
  id: root

  Poolsuite.Service {
    id: player
    manifest: ({ "__sourceDir": "/definitely/missing-poolsuite-plugin" })
  }

  Timer {
    interval: 1000
    running: true
    repeat: false
    onTriggered: {
      if (!player.busy && player.errorMessage ===
          "Could not start playback: The playback helper could not be launched") {
        console.log("PASS: helper launch failure surfaced")
        Qt.quit()
      } else {
        console.error("FAIL: launch failure was not surfaced: " + player.errorMessage)
        Qt.exit(1)
      }
    }
  }

  Component.onCompleted: player.toggle()
}
