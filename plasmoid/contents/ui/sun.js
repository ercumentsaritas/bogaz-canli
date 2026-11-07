.pragma library
// Gunes yuksekligi (NOAA yaklasimi) ve saate gore isik programi. Istanbul: 41.02 K, 28.98 D
var LAT = 41.02, LON = 28.98;

function sunElevation(date) {
    var rad = Math.PI / 180;
    var y0 = Date.UTC(date.getUTCFullYear(), 0, 1);
    var hourUTC = date.getUTCHours() + date.getUTCMinutes() / 60 + date.getUTCSeconds() / 3600;
    var doy0 = Math.floor((date.getTime() - y0) / 86400000);
    var g = 2 * Math.PI / 365 * (doy0 + (hourUTC - 12) / 24);
    var eqt = 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g)
                        - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g));
    var decl = 0.006918 - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g) - 0.006758 * Math.cos(2 * g)
             + 0.000907 * Math.sin(2 * g) - 0.002697 * Math.cos(3 * g) + 0.00148 * Math.sin(3 * g);
    var tst = hourUTC * 60 + eqt + 4 * LON;
    var ha = (tst / 4 - 180) * rad;
    var cz = Math.sin(LAT * rad) * Math.sin(decl) + Math.cos(LAT * rad) * Math.cos(decl) * Math.cos(ha);
    return 90 - Math.acos(Math.max(-1, Math.min(1, cz))) / rad;
}

// 0 = gunduz, 1 = gece. Gunes ufkun 1 derece ustunden sivil alacakaranliga (-6) kadar yumusak gecis.
function nightFactor(date) {
    var e = sunElevation(date);
    return Math.max(0, Math.min(1, (1 - e) / 7));
}

function lerp(t, t0, t1, v0, v1) {
    if (t <= t0) return v0;
    if (t >= t1) return v1;
    return v0 + (v1 - v0) * (t - t0) / (t1 - t0);
}

// Gece zaman ekseni: 12:00 -> 12 ... 23:59 -> 24, 03:00 -> 27, 06:00 -> 30
// Cuma ve Cumartesi geceleri sehir 1 saat gec yatar.
function nightClock(date) {
    var h = date.getHours() + date.getMinutes() / 60;
    var t = h < 12 ? h + 24 : h;
    var eveningDay = h < 12 ? (date.getDay() + 6) % 7 : date.getDay();   // 0=Paz ... 5=Cum, 6=Cmt
    var weekend = (eveningDay === 5 || eveningDay === 6);
    return { t: t, shift: weekend ? 1 : 0 };
}

// Aksam isiklari (bina pencerelerinin cogu): 23:00'ten sonra soner, sabah 06:00 civari yeniden yanar
function eveningLights(date) {
    var c = nightClock(date), t = c.t - c.shift;
    if (t < 29.5) return lerp(t, 23, 25.5, 1, 0.12);
    return lerp(t, 29.5, 30.75, 0.12, 0.7);
}

// Gec saat isiklari: 00:30'dan sonra azalir, 03:00'te %30'a iner, sabah artar
function lateLights(date) {
    var c = nightClock(date), t = c.t - c.shift;
    if (t < 29.5) return lerp(t, 24.5, 27, 1, 0.3);
    return lerp(t, 29.5, 30.75, 0.3, 0.9);
}
