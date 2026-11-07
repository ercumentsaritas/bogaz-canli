import QtQuick
import org.kde.plasma.plasmoid

WallpaperItem {
    id: root

    Scene {
        anchors.fill: parent
        serviceUrl: root.configuration.ServiceUrl
        fps: root.configuration.Fps
        showStatus: root.configuration.ShowStatus
        nightTint: root.configuration.NightTint
        shipScale: root.configuration.ShipScale
        running: root.visible
    }
}
