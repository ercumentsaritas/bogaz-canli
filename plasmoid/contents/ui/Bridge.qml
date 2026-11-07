import QtQuick

// 15 Temmuz Sehitler Koprusu LED aydinlatmasi (gorsel pikseli koordinatlari).
// Aski halatlari ve ana kablo boyunca yavasca akan renk gecisi.
Item {
    id: bridge
    property bool running: true
    property real phase: 0

    // tabliye kule noktalari ve kule tepeleri (gorselden olculdu)
    readonly property point deckA: Qt.point(1665, 405)
    readonly property point deckB: Qt.point(1776, 501)
    readonly property real towerH: 13          // kule tepesinin tabliyeden gorunen yuksekligi (px)
    readonly property point anchorA: Qt.point(1622, 368)   // yan aciklik ankrajlari
    readonly property point anchorB: Qt.point(1830, 548)
    readonly property int n: 44

    function hueAt(t) { return (phase + t * 0.35) % 1 }

    // tabliye uzerindeki sicak yol lambalari (sabit)
    Repeater {
        model: 30
        Rectangle {
            property real t: index / 29
            width: 1.6; height: 1.6; radius: 0.8
            x: bridge.anchorA.x + (bridge.anchorB.x - bridge.anchorA.x) * t - 0.8
            y: bridge.anchorA.y + (bridge.anchorB.y - bridge.anchorA.y) * t - 0.8
            color: "#ffe2a8"; opacity: 0.85
        }
    }

    // ana aciklik: aski halatlari + kablo uzerindeki LED'ler
    Repeater {
        model: bridge.n
        Item {
            id: hg
            property real t: (index + 0.5) / bridge.n
            property real sag: -bridge.towerH * Math.pow(2 * t - 1, 2)     // kablo, tabliyeye gore
            property real dx: bridge.deckA.x + (bridge.deckB.x - bridge.deckA.x) * t
            property real dy: bridge.deckA.y + (bridge.deckB.y - bridge.deckA.y) * t
            property color c: Qt.hsva(bridge.hueAt(t), 0.65, 1, 1)
            Rectangle {   // aski halati
                x: hg.dx - 0.4; y: hg.dy + hg.sag
                width: 0.8; height: Math.max(0.5, -hg.sag)
                color: hg.c; opacity: 0.3
            }
            Rectangle {   // kablo LED'i
                x: hg.dx - 1; y: hg.dy + hg.sag - 1
                width: 1.7; height: 1.7; radius: 0.85
                color: Qt.lighter(hg.c, 1.25); opacity: 0.95
            }
            Rectangle {   // hafif hare
                x: hg.dx - 3; y: hg.dy + hg.sag - 3
                width: 6; height: 6; radius: 3
                color: hg.c; opacity: 0.16
            }
        }
    }

    // yan acikliklar: kule tepesinden ankraja inen kablo
    Repeater {
        model: 16
        Rectangle {
            property bool sideA: index < 8
            property real t: ((index % 8) + 0.5) / 8
            property point from: sideA ? bridge.anchorA : Qt.point(bridge.deckB.x, bridge.deckB.y - bridge.towerH)
            property point to: sideA ? Qt.point(bridge.deckA.x, bridge.deckA.y - bridge.towerH) : bridge.anchorB
            width: 1.8; height: 1.8; radius: 0.9
            x: from.x + (to.x - from.x) * t - 0.9
            y: from.y + (to.y - from.y) * t - 0.9
            color: Qt.hsva(bridge.hueAt(sideA ? 0 : 1), 0.6, 1, 1); opacity: 0.8
        }
    }

    Timer {
        // ~40 sn'de tam renk turu; 5 Hz yeterli, sahneyi surekli yeniden cizmeye zorlamaz
        interval: 200; repeat: true; running: bridge.running && bridge.visible
        onTriggered: bridge.phase = (bridge.phase + 0.005) % 1
    }
}
