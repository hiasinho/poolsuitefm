import QtQuick
import QtQuick.Effects
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "io.github.hiasinho.poolsuitefm"

  readonly property var player: bar && bar.shell ? bar.shell.serviceFor(moduleName) : null
  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  readonly property bool popoutSwitchClosing: panelLoader.item
    ? panelLoader.item.popoutSwitchClosing === true
    : false

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
    if (panelLoader.item) panelLoader.item.open()
  }

  function close() {
    if (panelLoader.item) panelLoader.item.close()
  }

  function toggle() {
    if (panelLoader.item) panelLoader.item.toggle()
  }

  function closeForPopoutSwitch() {
    if (panelLoader.item) panelLoader.item.closeForPopoutSwitch()
  }

  function injectPanel() {
    var panel = panelLoader.item
    if (!panel) return
    panel.bar = root.bar
    panel.settings = root.settings
    panel.anchorItem = button
    panel.hostWidget = root
  }

  function pushSettings() {
    if (player && typeof player.applySettings === "function") player.applySettings(settings)
  }

  onBarChanged: injectPanel()
  onSettingsChanged: {
    injectPanel()
    pushSettings()
  }
  onPlayerChanged: pushSettings()
  Component.onCompleted: pushSettings()

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
    }
  }

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
        source: Qt.resolvedUrl("assets/icon.svg")
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
      ? (root.player.artist ? root.player.artist + " — " : "")
        + (root.player.title || root.stationName(root.player.station))
      : "Poolsuite FM"

    onPressed: function(code) {
      if (code === Qt.MiddleButton) {
        if (root.player && !root.player.busy) root.player.next()
      } else if (code === Qt.RightButton) {
        if (root.player && !root.player.busy) root.player.toggle()
      } else {
        root.toggle()
      }
    }

    onWheelMoved: function(delta) {
      if (!root.player || root.player.busy) return
      if (delta > 0) root.player.previous()
      else root.player.next()
    }
  }
}
