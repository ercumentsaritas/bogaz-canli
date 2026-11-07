.pragma library
// Enlem/boylam -> gorsel pikseli (2160x1440). Kontrol noktalarindan hesaplanan homografi.
var H = [229.2325651599, -47.6364370737, -4674.254293148, 11.4408859826, -238.9026120656, 9480.4860872198, 0.0058479821, -0.0281301187, 1.0];
var IMG_W = 2160, IMG_H = 1440;
function project(lat, lon) {
    var w = H[6]*lon + H[7]*lat + H[8];
    return { x: (H[0]*lon + H[1]*lat + H[2]) / w, y: (H[3]*lon + H[4]*lat + H[5]) / w };
}
// Rotadaki (derece, kuzeyden saat yonu) bir yonun ekrandaki aci karsiligi
function screenAngle(lat, lon, course) {
    var r = course * Math.PI / 180, d = 150;
    var lat2 = lat + Math.cos(r) * d / 110540;
    var lon2 = lon + Math.sin(r) * d / (111320 * Math.cos(lat * Math.PI / 180));
    var a = project(lat, lon), b = project(lat2, lon2);
    return Math.atan2(b.x - a.x, -(b.y - a.y)) * 180 / Math.PI;
}
// Hiz ve rotaya gore ileri tahmin (dead reckoning)
function advance(lat, lon, sogKn, course, seconds) {
    var m = sogKn * 0.514444 * seconds, r = course * Math.PI / 180;
    return { lat: lat + Math.cos(r) * m / 110540,
             lon: lon + Math.sin(r) * m / (111320 * Math.cos(lat * Math.PI / 180)) };
}
