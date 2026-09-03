import QtQuick
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "io.github.hiasinho.poolsuitefm"

  readonly property var player: bar && bar.shell ? bar.shell.serviceFor(moduleName) : null
  readonly property bool showTrack: setting("showTrack", true) === true
  property bool panelOpen: false
  property bool popoutSwitchClosing: false

  readonly property var stations: [
    { key: "official", name: "Official" },
    { key: "official2", name: "Official II" },
    { key: "mixtapes", name: "Mixtapes" },
    { key: "balearic", name: "Balearic Sundown" },
    { key: "indie", name: "Indie Summer" },
    { key: "tokyo", name: "Tokyo Disco" },
    { key: "friday", name: "Friday Nite Heat" },
    { key: "hangover", name: "Hangover Club" }
  ]

  function close() { panelOpen = false }
  function closeForPopoutSwitch() {
    popoutSwitchClosing = true
    close()
    Qt.callLater(function() { root.popoutSwitchClosing = false })
  }
  function pushSettings() {
    if (player && typeof player.applySettings === "function") player.applySettings(settings)
  }
  function stationName(key) {
    for (var i = 0; i < stations.length; i++) if (stations[i].key === key) return stations[i].name
    return "Poolsuite FM"
  }

  onSettingsChanged: pushSettings()
  onPlayerChanged: pushSettings()
  Component.onCompleted: pushSettings()

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    active: root.player && root.player.playing
    dimmed: !root.player || !root.player.running
    text: {
      var sun = root.player && root.player.playing ? "☀" : "☼"
      if (!root.showTrack || root.vertical || !root.player || !root.player.running) return sun
      var track = root.player.title || root.stationName(root.player.station)
      return sun + "  " + track
    }
    tooltipText: root.player && root.player.running
      ? (root.player.artist ? root.player.artist + " — " : "") + (root.player.title || root.stationName(root.player.station))
      : "Poolsuite FM"

    onPressed: function(code) {
      if (code === Qt.MiddleButton) {
        if (root.player) root.player.next()
      } else if (code === Qt.RightButton) {
        if (root.player) root.player.toggle()
      } else {
        root.panelOpen = !root.panelOpen
      }
    }
    onWheelMoved: function(delta) {
      if (!root.player) return
      if (delta > 0) root.player.previous()
      else root.player.next()
    }
  }

  KeyboardPanel {
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.panelOpen
    contentWidth: fittedContentWidth(Style.space(340))
    contentHeight: fittedContentHeight(content.implicitHeight)

    Column {
      id: content
      width: parent ? parent.width : 0
      spacing: Style.space(12)

      Column {
        width: parent.width
        spacing: Style.space(3)

        Text {
          width: parent.width
          text: root.player && root.player.title ? root.player.title : "Poolsuite FM"
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.subtitle
          font.bold: true
          elide: Text.ElideRight
        }
        Text {
          width: parent.width
          text: root.player && root.player.artist
            ? root.player.artist
            : root.stationName(root.player ? root.player.station : "official")
          color: Qt.darker(Color.popups.text, 1.4)
          font.family: Style.font.family
          font.pixelSize: Style.font.bodySmall
          elide: Text.ElideRight
        }
      }

      Row {
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Style.space(8)

        Button {
          iconText: "󰒮"
          foreground: Color.popups.text
          enabled: root.player && root.player.running
          onClicked: root.player.previous()
        }
        Button {
          iconText: root.player && root.player.playing ? "󰏤" : "󰐊"
          foreground: Color.popups.text
          onClicked: root.player.toggle()
        }
        Button {
          iconText: "󰒭"
          foreground: Color.popups.text
          enabled: root.player && root.player.running
          onClicked: root.player.next()
        }
        Button {
          iconText: "󰓛"
          tooltipText: "Stop"
          foreground: Color.popups.text
          enabled: root.player && root.player.running
          onClicked: root.player.stop()
        }
      }

      Row {
        width: parent.width
        spacing: Style.space(8)
        Text {
          text: "󰕾"
          color: Color.popups.text
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          anchors.verticalCenter: parent.verticalCenter
        }
        PanelSlider {
          width: parent.width - Style.space(34)
          bar: root.bar
          minimum: 0
          maximum: 100
          value: root.player ? root.player.volume : 70
          onReleased: function(value) { if (root.player) root.player.setVolume(value) }
        }
      }

      PanelSeparator { width: parent.width; foreground: Color.popups.text }

      Text {
        text: "CHANNELS"
        color: Qt.darker(Color.popups.text, 1.4)
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.bold: true
      }

      Grid {
        width: parent.width
        columns: 2
        spacing: Style.space(6)

        Repeater {
          model: root.stations
          Button {
            required property var modelData
            width: (content.width - Style.space(6)) / 2
            text: modelData.name
            leftAlign: true
            foreground: Color.popups.text
            selected: root.player && root.player.station === modelData.key
            onClicked: root.player.playStation(modelData.key)
          }
        }
      }

      Text {
        width: parent.width
        text: "Unofficial player · public Poolsuite SoundCloud playlists"
        color: Qt.darker(Color.popups.text, 1.6)
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        horizontalAlignment: Text.AlignHCenter
      }
    }
  }
}
