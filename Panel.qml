import QtQuick
import QtQuick.Effects
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "io.github.hiasinho.poolsuitefm"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  readonly property var player: bar && bar.shell ? bar.shell.serviceFor(moduleName) : null
  readonly property var barIdentity: hostWidget || root

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

  function stationName(key) {
    for (var i = 0; i < stations.length; i++) if (stations[i].key === key) return stations[i].name
    return "Poolsuite FM"
  }

  function open() {
    root.controller.show()
  }

  function close() {
    root.controller.hide()
  }

  function switchPanel(direction) {
    if (root.bar && typeof root.bar.switchPanelFrom === "function")
      return root.bar.switchPanelFrom(root.barIdentity, direction)
    return false
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(340))
    contentHeight: panel.fittedContentHeight(content.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Column {
        id: content
        width: parent.width
        spacing: Style.space(12)

        Row {
          width: parent.width
          spacing: Style.space(10)

          BorderSurface {
            width: Style.space(80)
            height: Style.space(80)
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
              width: Style.space(34)
              height: Style.space(34)
              source: Qt.resolvedUrl("assets/icon.svg")
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
            width: parent.width - Style.space(90)
            spacing: Style.space(3)
            anchors.verticalCenter: parent.verticalCenter

            Text {
              width: parent.width
              text: root.player && root.player.title ? root.player.title : "Poolsuite FM"
              textFormat: Text.PlainText
              color: Color.popups.text
              font.family: Style.font.family
              font.pixelSize: Style.font.subtitle
              font.bold: true
              elide: Text.ElideRight
            }

            Text {
              width: parent.width
              textFormat: Text.PlainText
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
            iconSize: Style.font.iconLarge
            horizontalPadding: Style.spacing.panelGap
            verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
            foreground: Color.popups.text
            enabled: root.player && root.player.running && !root.player.busy
            onClicked: root.player.previous()
          }

          Button {
            iconText: root.player && root.player.playing ? "󰏤" : "󰐊"
            iconSize: Style.font.iconLarge
            horizontalPadding: Style.spacing.panelGap
            verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
            foreground: Color.popups.text
            enabled: root.player && !root.player.busy
            onClicked: root.player.toggle()
          }

          Button {
            iconText: "󰒭"
            iconSize: Style.font.iconLarge
            horizontalPadding: Style.spacing.panelGap
            verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
            foreground: Color.popups.text
            enabled: root.player && root.player.running && !root.player.busy
            onClicked: root.player.next()
          }

          Button {
            iconText: "󰓛"
            iconSize: Style.font.iconLarge
            horizontalPadding: Style.spacing.panelGap
            verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
            tooltipText: "Stop"
            foreground: Color.popups.text
            enabled: root.player && root.player.running && !root.player.busy
            onClicked: root.player.stop()
          }
        }

        PanelSeparator {
          width: parent.width
          foreground: Color.popups.text
        }

        Text {
          text: "CHANNELS"
          textFormat: Text.PlainText
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
          textFormat: Text.PlainText
          color: Qt.darker(Color.popups.text, 1.6)
          font.family: Style.font.family
          font.pixelSize: Math.max(8, Style.font.caption - 2)
          horizontalAlignment: Text.AlignHCenter
          wrapMode: Text.WordWrap
        }
      }
    }
  }
}
