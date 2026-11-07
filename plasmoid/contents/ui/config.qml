import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    id: page
    property var configDialog
    property var wallpaperConfiguration: ({})
    property alias cfg_ServiceUrl: urlField.text
    property alias cfg_Fps: fpsSpin.value
    property alias cfg_ShowStatus: statusBox.checked
    property alias cfg_NightTint: nightBox.checked
    property real cfg_ShipScale: 1.0

    QQC2.TextField {
        id: urlField
        Kirigami.FormData.label: "Servis adresi:"
        Layout.minimumWidth: Kirigami.Units.gridUnit * 18
    }
    QQC2.SpinBox {
        id: fpsSpin
        Kirigami.FormData.label: "Kare hızı (FPS):"
        from: 2; to: 30
    }
    QQC2.Slider {
        id: scaleSlider
        Kirigami.FormData.label: "Gemi boyutu:"
        from: 0.5; to: 2.5; stepSize: 0.1
        value: page.cfg_ShipScale
        onMoved: page.cfg_ShipScale = value
    }
    QQC2.CheckBox { id: statusBox; text: "Köşede durum yazısını göster" }
    QQC2.CheckBox { id: nightBox; text: "Gece tonu ve gemi ışıkları" }
}
