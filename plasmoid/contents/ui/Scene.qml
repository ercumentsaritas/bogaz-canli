import QtQuick
import "geo.js" as Geo
import "sun.js" as Sun

// Saf QtQuick sahnesi: Plasma'dan bagimsiz, test edilebilir.
Item {
    id: scene
    clip: true

    property string serviceUrl: "http://127.0.0.1:8765/ships.json"
    property int fps: 10
    property int pollMs: 3000
    property bool showStatus: true
    property bool nightTint: true
    property real shipScale: 1.0
    property bool running: true
    property url background: Qt.resolvedUrl("../images/bosphorus.jpg")

    // durum
    property string mode: ""
    property int shipCount: 0
    property int realCount: 0
    property int liveTotal: 0
    property bool liveConfigured: false
    property bool liveConnected: false
    property bool serviceOk: false
    property var ships: ({})          // id -> Ship item
    property real serverOffset: 0     // localNow - serverNow (sn)

    // gece/gunduz: 0 = gunduz, 1 = tam gece (gunesin gercek yuksekligine gore)
    property real night: 0
    property real eveningOn: 1   // aksam isiklari (gece yarisindan sonra soner)
    property real lateOn: 1      // gec saat isiklari
    property var debugDate: null // test icin sabit saat
    function updateNight() {
        var d = debugDate ? debugDate : new Date()
        if (!nightTint) { night = 0; return }
        night = Sun.nightFactor(d)
        eveningOn = Sun.eveningLights(d)
        lateOn = Sun.lateLights(d)
    }

    Rectangle { anchors.fill: parent; color: "#0d3b55" }

    // Gorsel koordinatlarinda (2160x1440) calisan katman; ekrana "crop" ile olceklenir
    Item {
        id: layer
        width: Geo.IMG_W; height: Geo.IMG_H
        transformOrigin: Item.TopLeft
        scale: Math.max(scene.width / Geo.IMG_W, scene.height / Geo.IMG_H)
        x: (scene.width - Geo.IMG_W * scale) / 2
        y: (scene.height - Geo.IMG_H * scale) / 2

        Image {
            anchors.fill: parent
            source: scene.background
            fillMode: Image.Stretch
            asynchronous: true
            cache: false
            smooth: true
        }
        // gece gorseli: onceden islenmis sehir isiklari; gunduzle yumusak gecis
        Image {
            anchors.fill: parent
            source: scene.night > 0.01 ? Qt.resolvedUrl("../images/bosphorus_night.jpg") : ""
            opacity: scene.night
            visible: opacity > 0.01
            asynchronous: true
            cache: false
            smooth: true
        }
        // saate gore sonen bina isiklari
        Image {
            anchors.fill: parent
            source: scene.night > 0.01 ? Qt.resolvedUrl("../images/lights_evening.png") : ""
            opacity: scene.night * scene.eveningOn
            visible: opacity > 0.01
            asynchronous: true; cache: false; smooth: true
        }
        Image {
            anchors.fill: parent
            source: scene.night > 0.01 ? Qt.resolvedUrl("../images/lights_late.png") : ""
            opacity: scene.night * scene.lateOn
            visible: opacity > 0.01
            asynchronous: true; cache: false; smooth: true
        }
        // Kiz Kulesi
        Rectangle {
            visible: scene.night > 0.05; opacity: scene.night * 0.22
            width: 18; height: 18; radius: 9; x: 1290 - 9; y: 780 - 9
            color: "#ffcf7a"
        }
        Rectangle {
            visible: scene.night > 0.05; opacity: scene.night * 0.9
            width: 4; height: 4; radius: 2; x: 1290 - 2; y: 780 - 2
            color: "#fff1c4"
        }
        Bridge {
            anchors.fill: parent
            visible: scene.night > 0.05
            opacity: scene.night
            running: scene.running
        }
        Item { id: shipLayer; anchors.fill: parent }
    }

    Text {
        visible: scene.showStatus
        anchors { left: parent.left; bottom: parent.bottom; margins: 14 }
        color: "white"; opacity: 0.55
        font.pixelSize: 12
        style: Text.Raised; styleColor: "#80000000"
        text: {
            if (!scene.serviceOk) return "⚓ AIS servisi bekleniyor…"
            if (scene.mode === "live") return "● CANLI AIS · " + scene.shipCount + " gemi"
            if (scene.mode === "hybrid") return "● " + scene.realCount + " canlı gemi (Marmara'da " + scene.liveTotal + ") + tarifeli vapurlar ve simülasyon"
            if (scene.liveConfigured && !scene.liveConnected) return "◌ AIS bağlantısı yok · tarifeli vapurlar + simülasyon"
            if (scene.liveConfigured)
                return "◌ tarifeli vapurlar + simülasyon · AIS bağlı: Marmara'da " + scene.liveTotal + " canlı gemi, Boğaz'da yok"
            return "◌ tarifeli vapurlar + simülasyon"
        }
    }

    Component { id: shipComp; Ship {} }

    function poll() {
        var xhr = new XMLHttpRequest()
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE) return
            if (xhr.status !== 200) { serviceOk = false; return }
            try { apply(JSON.parse(xhr.responseText)) } catch (e) { console.warn("bogaz:", e); serviceOk = false }
        }
        xhr.open("GET", serviceUrl + (serviceUrl.indexOf("?") < 0 ? "?" : "&") + "_=" + Date.now())
        xhr.send()
    }

    function apply(data) {
        serviceOk = true
        mode = data.mode
        realCount = data.real || 0
        liveTotal = data.liveTotal || 0
        liveConfigured = !!data.liveConfigured
        liveConnected = !!data.connected
        serverOffset = Date.now() / 1000 - data.time
        var seen = {}, n = 0
        for (var i = 0; i < data.ships.length; i++) {
            var s = data.ships[i]
            var p = Geo.project(s.lat, s.lon)
            // gorselin cok disindakileri atla
            if (p.x < -200 || p.y < -200 || p.x > Geo.IMG_W + 200 || p.y > Geo.IMG_H + 200) continue
            seen[s.id] = true; n++
            var item = ships[s.id]
            if (!item) {
                item = shipComp.createObject(shipLayer, { category: s.cat || "other" })
                item.night = Qt.binding(function() { return scene.night })
                item.shipScale = Qt.binding(function() { return scene.shipScale })
                ships[s.id] = item
            }
            item.update(s, data.time, s.len || 0)
        }
        for (var id in ships) {
            if (!seen[id]) { ships[id].retire(); delete ships[id] }
        }
        shipCount = n
    }

    function frame() {
        var serverNow = Date.now() / 1000 - serverOffset
        for (var id in ships) ships[id].tick(serverNow, layer.scale)
    }

    Timer { interval: scene.pollMs; running: scene.running; repeat: true; triggeredOnStart: true; onTriggered: scene.poll() }
    Timer { interval: Math.round(1000 / Math.max(1, scene.fps)); running: scene.running; repeat: true; onTriggered: scene.frame() }
    Timer { interval: 30000; running: true; repeat: true; triggeredOnStart: true; onTriggered: scene.updateNight() }
    onNightTintChanged: updateNight()
}
