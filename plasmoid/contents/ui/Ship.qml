import QtQuick
import "geo.js" as Geo

// Tek bir gemi. Koordinatlar gorsel pikseli (2160x1440) cinsinden.
Item {
    id: ship
    property string category: "other"
    property real lengthM: 0
    property real shipScale: 1.0
    property real night: 0

    // son AIS raporu
    property real lat0: 0
    property real lon0: 0
    property real sog: 0
    property real cog: 0
    property var hdg: null
    property real t0: 0
    property bool placed: false
    property real angle: 0

    readonly property var defaultLen: ({ cargo: 150, tanker: 180, passenger: 70, tug: 30,
                                         pleasure: 15, hsc: 30, other: 60 })
    readonly property real metersPerPx: 6.5
    property real hullLen: Math.max(8, (lengthM > 0 ? lengthM : (defaultLen[category] || 60)) / metersPerPx * shipScale)

    width: hullLen * 0.2
    height: hullLen
    rotation: angle
    opacity: 0
    Behavior on opacity { NumberAnimation { duration: 1500 } }

    // dumen suyu: geminin kicinda, hiza gore uzar
    Image {
        id: wake
        source: Qt.resolvedUrl("../images/ships/wake.svg")
        property real k: Math.min(1, ship.sog / 12)
        width: ship.width * 3.2
        height: ship.hullLen * (0.6 + 2.2 * k)
        x: (ship.width - width) / 2
        y: ship.height * 0.55
        opacity: ship.sog < 0.7 ? 0 : (0.35 + 0.5 * k) * (1 - ship.night * 0.5)
        visible: opacity > 0
        sourceSize: Qt.size(60, 200)
        smooth: true
    }

    Image {
        anchors.fill: parent
        source: Qt.resolvedUrl("../images/ships/" + ship.category + ".svg")
        sourceSize: Qt.size(Math.max(20, Math.ceil(ship.width * 4)), Math.max(100, Math.ceil(ship.height * 4)))
        smooth: true
        mipmap: true
        opacity: 1 - ship.night * 0.4
    }

    // gece seyir fenerleri
    Rectangle {
        visible: ship.night > 0.25
        opacity: ship.night
        width: Math.max(3, ship.width * 0.9); height: width; radius: width / 2
        x: (ship.width - width) / 2; y: ship.height * 0.12
        color: "#fff6c8"
    }
    Rectangle {
        visible: ship.night > 0.25
        opacity: ship.night * 0.14
        width: Math.max(8, ship.hullLen * 0.45); height: width; radius: width / 2
        x: (ship.width - width) / 2; y: ship.height * 0.5 - height / 2
        color: "#ffd98a"
    }

    function update(s, serverTime, len) {
        lat0 = s.lat; lon0 = s.lon
        sog = s.sog || 0
        cog = s.cog || 0
        hdg = (s.hdg === null || s.hdg === undefined) ? null : s.hdg
        t0 = s.t || serverTime
        if (s.cat) category = s.cat
        if (len) lengthM = len
        opacity = 1
    }

    function tick(serverNow, layerScale) {
        var age = Math.max(0, Math.min(serverNow - t0, 180))   // en fazla 3 dk ileri tahmin
        var pos = sog > 0.5 ? Geo.advance(lat0, lon0, sog, cog, age) : { lat: lat0, lon: lon0 }
        var p = Geo.project(pos.lat, pos.lon)
        var tx = p.x - width / 2, ty = p.y - height / 2
        var course = (hdg !== null && (sog < 2 || Math.abs(((hdg - cog + 540) % 360) - 180) < 60)) ? hdg : cog
        var ta = Geo.screenAngle(pos.lat, pos.lon, course)
        if (!placed || Math.abs(tx - x) + Math.abs(ty - y) > 80) {
            x = tx; y = ty; angle = ta; placed = true
            return
        }
        x += (tx - x) * 0.3
        y += (ty - y) * 0.3
        var da = ((ta - angle + 540) % 360) - 180
        angle += da * 0.15
    }

    function retire() {
        opacity = 0
        destroy(1800)
    }
}
