import QtQuick
import QtQuick.Effects
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "io.github.hiasinho.poolsuitefm"

  readonly property var player: bar && bar.shell ? bar.shell.serviceFor(moduleName) : null
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
    text: ""
    labelVisible: false
    hasVisualContent: true
    fixedWidth: root.vertical ? barSize : Style.space(14) + scaledHorizontalMargin * 2

    Item {
      width: Style.space(14)
      height: Style.space(14)
      anchors.centerIn: parent

      Image {
        id: palmIcon
        anchors.fill: parent
        source: Qt.resolvedUrl("assets/favicon.png")
        sourceSize.width: Math.round(width * Screen.devicePixelRatio)
        sourceSize.height: Math.round(height * Screen.devicePixelRatio)
        fillMode: Image.PreserveAspectFit
        smooth: false
        visible: false
        layer.enabled: true
      }

      MultiEffect {
        anchors.fill: palmIcon
        source: palmIcon
        colorization: 1.0
        colorizationColor: button.active && button.useActiveColor ? button.activeColor : button.foreground
      }
    }

    tooltipText: root.player && root.player.running
      ? (root.player.artist ? root.player.artist + " — " : "") + (root.player.title || root.stationName(root.player.station))
      : "Poolsuite FM"

    onPressed: function(code) {
      if (code === Qt.MiddleButton) {
        if (root.player && !root.player.busy) root.player.next()
      } else if (code === Qt.RightButton) {
        if (root.player && !root.player.busy) root.player.toggle()
      } else {
        root.panelOpen = !root.panelOpen
      }
    }
    onWheelMoved: function(delta) {
      if (!root.player || root.player.busy) return
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

      Row {
        width: parent.width
        spacing: Style.space(10)

        BorderSurface {
          width: Style.space(64)
          height: Style.space(64)
          radius: Style.spacing.labelGap
          color: Style.normalFillFor(Color.popups.text, Color.accent)
          borderSpec: Border.controlSpec("normal", Color.popups.text, Color.accent)

          Image {
            id: coverArt
            anchors.fill: parent
            anchors.margins: Style.space(2)
            source: root.player ? root.player.artUrl : ""
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            visible: status === Image.Ready
          }

          Image {
            id: fallbackIcon
            anchors.centerIn: parent
            width: Style.space(28)
            height: Style.space(28)
            source: Qt.resolvedUrl("assets/favicon.png")
            visible: false
            layer.enabled: true
          }

          MultiEffect {
            anchors.fill: fallbackIcon
            source: fallbackIcon
            colorization: 1.0
            colorizationColor: Color.popups.text
            visible: coverArt.status !== Image.Ready
          }
        }

        Column {
          width: parent.width - Style.space(74)
          spacing: Style.space(3)
          anchors.verticalCenter: parent.verticalCenter

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
      }

      Row {
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Style.space(8)

        Button {
          iconText: "󰒮"
          foreground: Color.popups.text
          enabled: root.player && root.player.running && !root.player.busy
          onClicked: root.player.previous()
        }
        Button {
          iconText: root.player && root.player.playing ? "󰏤" : "󰐊"
          foreground: Color.popups.text
          enabled: root.player && !root.player.busy
          onClicked: root.player.toggle()
        }
        Button {
          iconText: "󰒭"
          foreground: Color.popups.text
          enabled: root.player && root.player.running && !root.player.busy
          onClicked: root.player.next()
        }
        Button {
          iconText: "󰓛"
          tooltipText: "Stop"
          foreground: Color.popups.text
          enabled: root.player && root.player.running && !root.player.busy
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
          enabled: root.player && !root.player.busy
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
            enabled: root.player && !root.player.busy
            onClicked: root.player.playStation(modelData.key)
          }
        }
      }

      Text {
        width: parent.width
        text: "Unofficial player\nPublic Poolsuite SoundCloud playlists"
        color: Qt.darker(Color.popups.text, 1.6)
        font.family: Style.font.family
        font.pixelSize: Math.max(8, Style.font.caption - 2)
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
      }
    }
  }
}
