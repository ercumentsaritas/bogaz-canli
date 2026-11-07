#!/usr/bin/env python3
"""
Bogaz Canli - AIS servisi
Istanbul Bogazi'ndaki gemileri localhost'ta JSON olarak sunar.
  * AISStream.io API anahtari varsa: canli AIS verisi
  * Yoksa (ya da canli veri gelmiyorsa): gercekci simulasyon
Yalnizca Python standart kutuphanesi gerekir; canli mod icin ek olarak `websockets`.
"""
import asyncio, json, math, os, random, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONFIG_PATH = os.path.expanduser("~/.config/bogaz-canli/config.json")
DEFAULTS = {"api_key": "", "mode": "auto", "port": 8765, "stale_minutes": 15,
            "fallback_after_seconds": 300}
# Gorselin kapsadigi alan (biraz payli): [[lat_min, lon_min], [lat_max, lon_max]]
BBOX = [[40.50, 28.00], [41.30, 29.60]]   # Marmara'nin dogusu; gorsel disindakiler sadece sayilir
SIM_ROUTES = json.loads('{"transit":{"NB":[[40.968919,28.992908],[40.988972,28.995686],[41.01231,28.999277],[41.021124,28.999789],[41.027877,29.009624],[41.03545,29.025958],[41.043522,29.036803],[41.05908,29.049937],[41.074665,29.050084]],"SB":[[41.074507,29.046776],[41.058904,29.045848],[41.046598,29.032977],[41.039083,29.021831],[41.031227,29.004887],[41.017409,28.99709],[40.988857,28.990328],[40.968782,28.983854]],"SB_W":[[41.074507,29.046776],[41.058904,29.045848],[41.046598,29.032977],[41.039083,29.021831],[41.031227,29.004887],[41.017365,28.995671],[40.99247,28.973508],[40.976952,28.93507],[40.970496,28.904893]],"NB_W":[[40.969246,28.904633],[40.973954,28.938254],[40.990167,28.97694],[41.004694,28.996658],[41.01231,28.999277],[41.021124,28.999789],[41.027877,29.009624],[41.03545,29.025958],[41.043522,29.036803],[41.05908,29.049937],[41.074665,29.050084]]},"ferries":{"Kadikoy-Eminonu":[[40.99275,29.020923],[40.993436,29.015831],[40.994908,29.0105],[40.997143,29.004661],[41.013515,28.989729],[41.019178,28.983843],[41.018327,28.975041]],"Kadikoy-Karakoy":[[40.99275,29.020923],[40.993436,29.015831],[40.994908,29.0105],[40.997143,29.004661],[41.014275,28.990495],[41.0206,28.983268],[41.02128,28.977627]],"Uskudar-Eminonu":[[41.028133,29.013007],[41.024036,29.001011],[41.01954,28.983874],[41.018327,28.975041]],"Uskudar-Besiktas":[[41.028133,29.013007],[41.034219,29.010926],[41.038774,29.008009]],"Kadikoy-Besiktas":[[40.99275,29.020923],[40.993436,29.015831],[40.994908,29.0105],[40.997143,29.004661],[41.008586,29.000143],[41.01673,28.998823],[41.033315,29.004991],[41.038774,29.008009]]},"halic":[[41.018905,28.975099],[41.020517,28.969383],[41.022311,28.965461],[41.025271,28.963428],[41.028634,28.960126],[41.030848,28.954711],[41.033471,28.952085],[41.035776,28.950768],[41.037713,28.949082],[41.038957,28.946977],[41.039863,28.944832],[41.041473,28.944116],[41.043073,28.943404],[41.045309,28.942804]],"anchor":[[40.980567,28.940727],[40.986353,28.948098],[40.977532,28.953472],[40.99059,28.96023],[40.98267,28.965147],[40.97534,28.970303],[40.970786,28.948872],[40.9722,28.932841]],"ferry_paths":{"KAD_KAR":[[40.99275,29.020923],[40.993436,29.015831],[40.994908,29.0105],[40.997143,29.004661],[41.014275,28.990495],[41.0206,28.983268],[41.02128,28.977627]],"KAR_EMI":[[41.02128,28.977627],[41.020026,28.976463],[41.018327,28.975041]],"KAD_EMI":[[40.99275,29.020923],[40.993436,29.015831],[40.994908,29.0105],[40.997143,29.004661],[41.013515,28.989729],[41.019178,28.983843],[41.018327,28.975041]],"USK_EMI":[[41.028133,29.013007],[41.024036,29.001011],[41.01954,28.983874],[41.018327,28.975041]],"USK_KAR":[[41.028133,29.013007],[41.024036,29.001011],[41.020262,28.983936],[41.02128,28.977627]],"KAD_BES":[[40.99275,29.020923],[40.993436,29.015831],[40.994908,29.0105],[40.997143,29.004661],[41.008586,29.000143],[41.01673,28.998823],[41.033315,29.004991],[41.038774,29.008009]],"USK_BES":[[41.028133,29.013007],[41.034219,29.010926],[41.038774,29.008009]],"HALIC":[[41.02128,28.977627],[41.020026,28.976463],[41.018905,28.975099],[41.020517,28.969383],[41.022311,28.965461],[41.025271,28.963428],[41.028634,28.960126],[41.030848,28.954711],[41.033471,28.952085],[41.035776,28.950768],[41.037713,28.949082],[41.038957,28.946977],[41.039863,28.944832],[41.041473,28.944116],[41.043073,28.943404],[41.045309,28.942804]]}}')

def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)

def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    except Exception as e:
        log("config okunamadi:", e)
    if os.environ.get("BOGAZ_API_KEY"):
        cfg["api_key"] = os.environ["BOGAZ_API_KEY"]
    if os.environ.get("BOGAZ_MODE"):
        cfg["mode"] = os.environ["BOGAZ_MODE"]
    return cfg

def category(t):
    if t is None: return "other"
    if 60 <= t <= 69: return "passenger"
    if 70 <= t <= 79: return "cargo"
    if 80 <= t <= 89: return "tanker"
    if t in (31, 32, 52): return "tug"
    if t in (36, 37): return "pleasure"
    if 40 <= t <= 49: return "hsc"
    return "other"

# ---------------------------------------------------------------- canli AIS
class LiveFeed:
    URL = "wss://stream.aisstream.io/v0/stream"

    def __init__(self, cfg):
        self.cfg = cfg
        self.ships = {}
        self.static = {}
        self.lock = threading.Lock()
        self.connected = False
        self.last_msg = 0.0
        self.started = time.time()

    def snapshot(self):
        cutoff = time.time() - self.cfg["stale_minutes"] * 60
        with self.lock:
            for k in [k for k, s in self.ships.items() if s["t"] < cutoff]:
                del self.ships[k]
            out = []
            for mmsi, s in self.ships.items():
                st = self.static.get(mmsi, {})
                d = dict(s)
                d.update({k: v for k, v in st.items() if v is not None})
                out.append(d)
            return out

    def handle(self, msg):
        mt = msg.get("MessageType")
        meta = msg.get("MetaData", {})
        mmsi = meta.get("MMSI")
        body = msg.get("Message", {}).get(mt, {})
        if not mmsi or not body:
            return
        self.last_msg = time.time()
        if mt in ("PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport"):
            lat, lon = body.get("Latitude"), body.get("Longitude")
            if lat is None or lon is None or abs(lat) > 90:
                return
            hdg = body.get("TrueHeading")
            if hdg is None or hdg >= 360: hdg = None
            cog = body.get("Cog")
            if cog is None or cog >= 360: cog = hdg if hdg is not None else 0
            sog = body.get("Sog") or 0
            if sog >= 102.2: sog = 0
            with self.lock:
                self.ships[mmsi] = {"id": mmsi, "name": (meta.get("ShipName") or "").strip(),
                                    "lat": lat, "lon": lon, "sog": sog, "cog": cog, "hdg": hdg,
                                    "nav": body.get("NavigationalStatus"), "t": time.time(),
                                    "cat": self.static.get(mmsi, {}).get("cat", "other")}
        elif mt == "ShipStaticData" or mt == "StaticDataReport":
            t = body.get("Type")
            if t is None:
                t = body.get("ReportB", {}).get("ShipType")
            dim = body.get("Dimension") or body.get("ReportB", {}).get("Dimension") or {}
            length = (dim.get("A") or 0) + (dim.get("B") or 0)
            with self.lock:
                st = self.static.setdefault(mmsi, {})
                if t is not None: st["cat"] = category(t)
                if length: st["len"] = length
                name = (body.get("Name") or body.get("ReportA", {}).get("Name") or "").strip()
                if name: st["name"] = name

    async def run(self):
        try:
            import websockets
        except ImportError:
            log("HATA: 'websockets' paketi yok -> sudo dnf install python3-websockets")
            return
        backoff = 5
        quick_drops = 0
        while True:
            opened = time.time()
            try:
                async with websockets.connect(self.URL, ping_interval=30, max_size=2**20) as ws:
                    await ws.send(json.dumps({
                        "APIKey": self.cfg["api_key"],
                        "BoundingBoxes": [BBOX],
                        "FilterMessageTypes": ["PositionReport", "StandardClassBPositionReport",
                                               "ExtendedClassBPositionReport", "ShipStaticData",
                                               "StaticDataReport"]}))
                    self.connected = True
                    log("AISStream baglandi")
                    async for raw in ws:
                        try:
                            m = json.loads(raw)
                        except ValueError:
                            continue
                        if "error" in m:
                            log("AISStream hatasi:", m["error"])
                            break
                        self.handle(m)
            except Exception as e:
                log("baglanti koptu:", type(e).__name__, e)
            self.connected = False
            if time.time() - opened < 5:
                quick_drops += 1
                if quick_drops == 3:
                    log("UYARI: AISStream baglantiyi hemen kapatiyor -> API anahtari gecersiz olabilir")
                backoff = min(backoff * 2, 300)
            else:
                quick_drops = 0
                backoff = 5
            await asyncio.sleep(backoff)

    def start(self):
        threading.Thread(target=lambda: asyncio.run(self.run()), daemon=True).start()

# ---------------------------------------------------------------- simulasyon
M_PER_DEG_LAT = 110540.0
KN = 0.514444

def seg_info(path):
    lat0 = math.radians(path[0][0])
    segs, total = [], 0.0
    for (a, b), (c, d) in zip(path, path[1:]):
        dy = (c - a) * M_PER_DEG_LAT
        dx = (d - b) * 111320.0 * math.cos(lat0)
        L = math.hypot(dx, dy)
        segs.append((a, b, c, d, L, (math.degrees(math.atan2(dx, dy)) + 360) % 360))
        total += L
    return segs, total

def along(path_info, s):
    segs, total = path_info
    s = max(0.0, min(s, total))
    for a, b, c, d, L, brg in segs:
        if s <= L or L == 0:
            f = s / L if L else 0
            return a + (c - a) * f, b + (d - b) * f, brg
        s -= L
    a, b, c, d, L, brg = segs[-1]
    return c, d, brg

NAMES = ["ANADOLU STAR", "MARMARA SPIRIT", "KARADENIZ", "AEGEAN DAWN", "BOSPHORUS TRADER",
         "NORDIC HAWK", "ODESSA LINK", "VOLGA RIVER", "CONSTANTA", "BLUE HORIZON",
         "SILVER WAVE", "PONTUS", "TRABZON", "SAMSUN", "MEDITERRANEAN", "NOVOROSSIYSK"]

class Sim:
    def __init__(self):
        self.ships = []
        self.next_id = 900000001
        self.transit = {k: (v, seg_info(v)) for k, v in SIM_ROUTES["transit"].items()}
        self.pending = []  # (respawn_time)
        for i in range(7):
            self.spawn_transit(progress=random.random())
        for p in SIM_ROUTES["anchor"][:0]:  # demirli gemiler kapali
            self.ships.append({"kind": "anchor", "id": self.nid(), "name": random.choice(NAMES),
                               "cat": random.choice(["cargo", "tanker", "cargo"]),
                               "len": random.randint(140, 230), "lat": p[0], "lon": p[1],
                               "base": random.uniform(0, 360), "phase": random.uniform(0, 6.28)})

    def nid(self):
        self.next_id += 1
        return self.next_id

    def spawn_transit(self, progress=0.0):
        key = random.choice(list(self.transit))
        path, info = self.transit[key]
        self.ships.append({"kind": "transit", "id": self.nid(), "name": random.choice(NAMES),
                           "cat": random.choice(["cargo", "cargo", "tanker", "tanker", "cargo", "other"]),
                           "len": random.randint(90, 260), "info": info,
                           "s": progress * info[1], "v": random.uniform(8, 12.5) * KN})

    def make_ferry(self, name, path, info, progress, speed=None):
        return {"kind": "ferry", "id": self.nid(), "name": "VAPUR " + name.upper(), "cat": "passenger",
                "len": 70 if speed is None else 40, "info": info, "s": progress * info[1], "dir": 1,
                "v": (speed or random.uniform(11.5, 14)) * KN, "dwell": 0.0}

    def step(self, dt):
        now = time.time()
        for sh in list(self.ships):
            if sh["kind"] == "transit":
                sh["s"] += sh["v"] * dt
                if sh["s"] >= sh["info"][1]:
                    self.ships.remove(sh)
                    self.pending.append(now + random.uniform(20, 150))
            elif sh["kind"] == "ferry":
                if sh["dwell"] > 0:
                    sh["dwell"] -= dt
                    continue
                total = sh["info"][1]
                # iskeleye yaklasirken/kalkarken yavasla
                dist_end = (total - sh["s"]) if sh["dir"] > 0 else sh["s"]
                dist_start = sh["s"] if sh["dir"] > 0 else (total - sh["s"])
                f = max(0.25, min(1.0, dist_end / 250.0, (dist_start + 40) / 200.0))
                sh["cur_v"] = sh["v"] * f
                sh["s"] += sh["dir"] * sh["cur_v"] * dt
                if sh["s"] >= total or sh["s"] <= 0:
                    sh["s"] = min(max(sh["s"], 0), total)
                    sh["dir"] *= -1
                    sh["dwell"] = random.uniform(60, 150)
        for t in [t for t in self.pending if t <= now]:
            self.pending.remove(t)
            self.spawn_transit()

    def snapshot(self):
        now = time.time()
        out = []
        for sh in self.ships:
            d = {"id": sh["id"], "name": sh["name"], "cat": sh["cat"], "len": sh["len"], "t": now}
            if sh["kind"] == "anchor":
                hdg = (sh["base"] + 25 * math.sin(now / 900.0 + sh["phase"])) % 360
                d.update(lat=sh["lat"], lon=sh["lon"], sog=0.0, cog=hdg, hdg=round(hdg), nav=1)
            else:
                lat, lon, brg = along(sh["info"], sh["s"])
                moving = sh.get("dwell", 0) <= 0
                if sh["kind"] == "ferry" and sh["dir"] < 0:
                    brg = (brg + 180) % 360
                v = sh.get("cur_v", sh["v"]) if moving else 0.0
                d.update(lat=lat, lon=lon, sog=round(v / KN, 1), cog=round(brg, 1),
                         hdg=round(brg), nav=0 if moving else 5)
            out.append(d)
        return out

    def start(self):
        def loop():
            last = time.time()
            while True:
                time.sleep(1.0)
                now = time.time()
                self.step(now - last)
                last = now
        threading.Thread(target=loop, daemon=True).start()

# ---------------------------------------------------------------- tarifeli vapurlar
# Kaynak: Sehir Hatlari 2026-2027 kis tarifesi (e-yasamrehberi.com, 7 Eylul 2026 guncellemesi).
# Gun tipleri: all = her gun, wd = hafta ici, ms = Pzt-Cmt, fs = yalniz Cuma ve Cumartesi gecesi
# (gece yarisindan sonraki saatler bir onceki gunun servisine sayilir).
# Uskudar-Besiktas (Dentur) ve Halic hatti icin tam tarife yayinlanmadigindan yaklasik siklik kullanilir.
def _every(start, end, step):
    h, m = map(int, start.split(":")); eh, em = map(int, end.split(":"))
    a, b = h * 60 + m, eh * 60 + em
    if b < a: b += 1440
    return " ".join("%02d:%02d" % ((t // 60) % 24, t % 60) for t in range(a, b + 1, step))

TIMETABLE = [
 # (hat adi, [(gun_tipi, "saatler")], [(yol, ters_mi, sure_dk, iskelede_bekleme_dk), ...])
 ("KADIKOY-KARAKOY-EMINONU",
  [("wd", "06:10"), ("ms", "06:30 06:45"),
   ("all", _every("07:00", "20:00", 20))],
  [("KAD_KAR", False, 17, 3), ("KAR_EMI", False, 3, 0)]),
 ("KADIKOY-KARAKOY",
  [("all", "20:30 21:00 21:30 22:00 22:30 23:00 23:30 00:00 00:30 01:00")],
  [("KAD_KAR", False, 20, 0)]),
 ("EMINONU-KADIKOY",
  [("ms", "07:15"),
   ("all", "07:30 07:50 08:10 08:30 08:50 09:10 09:35 09:55 10:15 10:35 10:55 11:15 11:35 11:55 "
           "12:15 12:35 12:55 13:15 13:35 13:55 14:15 14:35 14:55 15:15 15:35 15:55 16:15 16:35 "
           "16:55 17:15 17:35 17:55 18:15 18:35 18:55 19:15 19:35 19:55 20:15 20:35 21:05")],
  [("KAD_EMI", True, 20, 0)]),
 ("KARAKOY-KADIKOY",
  [("wd", "06:35"), ("ms", "06:55"),
   ("all", "21:30 22:00 22:30 23:00 23:30 00:00 00:30 01:00")],
  [("KAD_KAR", True, 20, 0)]),
 ("USKUDAR-KARAKOY-EMINONU",
  [("all", "07:00 08:00 09:00 09:20 09:40 10:00 10:20 10:40 11:00 11:20 11:40 12:00 12:20 12:40 "
           "13:00 13:20 13:40 14:00 14:20 14:40 15:00 16:00 16:20 17:20 18:20")],
  [("USK_KAR", False, 13, 2), ("KAR_EMI", False, 3, 0)]),
 ("USKUDAR-EMINONU",
  [("ms", "06:25 06:40"),
   ("all", "07:20 07:40 08:20 08:40 15:20 15:40 16:40 17:00 17:40 18:00 18:40 19:00 19:20 19:40 "
           "20:00 20:30 21:00 21:30 22:00")],
  [("USK_EMI", False, 15, 0)]),
 ("EMINONU-USKUDAR",
  [("ms", "06:40 07:00"),
   ("all", "07:20 07:40 08:00 08:20 08:40 09:00 09:25 09:45 10:05 10:25 10:45 11:05 11:25 11:45 "
           "12:05 12:25 12:45 13:05 13:25 13:45 14:05 14:25 14:45 15:05 15:25 15:45 16:05 16:25 "
           "16:45 17:05 17:25 17:45 18:05 18:25 18:45 19:00 19:20 19:40 20:00 20:30 21:00 21:30 "
           "22:00 22:30")],
  [("USK_EMI", True, 15, 0)]),
 ("KADIKOY-BESIKTAS",
  [("wd", "06:45"), ("ms", "07:20"), ("all", _every("07:45", "23:15", 30)),
   ("fs", "23:45 00:15 00:45 01:15 01:30 02:35 03:45 04:55")],
  [("KAD_BES", False, 25, 0)]),
 ("BESIKTAS-KADIKOY",
  [("wd", "07:15"), ("ms", "07:45"), ("all", _every("08:15", "23:45", 30)),
   ("fs", "00:15 00:45 01:15 01:45 02:05 03:10 04:20 05:30")],
  [("KAD_BES", True, 25, 0)]),
 ("USKUDAR-BESIKTAS",                       # Dentur, yaklasik 15 dk arayla
  [("all", _every("06:10", "00:45", 15))],
  [("USK_BES", False, 7, 0)]),
 ("BESIKTAS-USKUDAR",
  [("all", _every("06:20", "00:50", 15))],
  [("USK_BES", True, 7, 0)]),
 ("HALIC",                                  # yaklasik, saatlik
  [("all", _every("07:30", "20:30", 60))],
  [("HALIC", False, 25, 0)]),
 ("HALIC-DONUS",
  [("all", _every("08:15", "21:15", 60))],
  [("HALIC", True, 25, 0)]),
]

FERRY_NAMES = ["FENERBAHCE", "KADIKOY", "BEYKOZ", "BARIS MANCO", "TURGUT OZAL", "SEMIHA SAKIR",
               "ERTUGRUL GAZI", "MEHMET AKIF ERSOY", "KAPTAN DERYA", "NAZIM HIKMET", "ORHAN GAZI",
               "PAKSOY", "SAIT FAIK", "SEHIT MUSTAFA", "HALIC 1", "KUZGUNCUK"]

def _runs_on(daytype, service_wd):
    # service_wd: 0=Pzt ... 6=Paz (servis gununun gunu)
    if daytype == "all": return True
    if daytype == "wd": return service_wd <= 4
    if daytype == "ms": return service_wd <= 5
    if daytype == "fs": return service_wd in (4, 5)
    return False

class Ferries:
    BEFORE = 6 * 60      # kalkistan once iskelede bekleme (sn)
    AFTER = 3 * 60       # varistan sonra iskelede kalma (sn)

    def __init__(self, paths):
        self.paths = {k: seg_info(v) for k, v in paths.items()}
        self.trips = []  # (line, minutes_from_service_day_start, daytype, legs)
        for line, times, legs in TIMETABLE:
            for daytype, s in times:
                for hm in s.split():
                    h, m = map(int, hm.split(":"))
                    mins = h * 60 + m + (1440 if h < 5 else 0)   # gece yarisindan sonrasi -> onceki gun
                    self.trips.append((line, mins, daytype, legs))

    @staticmethod
    def _now_local():
        try:
            from zoneinfo import ZoneInfo
            import datetime
            return datetime.datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            import datetime
            return datetime.datetime.now()

    def _leg_state(self, info, reverse, dur_s, t):
        """t: legin baslangicindan beri gecen sn -> (lat, lon, brg, sog_kn)"""
        L = info[1]
        a = min(70.0, dur_s / 4); b = min(100.0, dur_s / 4)
        v = L / max(1.0, dur_s - a / 2 - b / 2)
        if t <= 0: s, sp = 0.0, 0.0
        elif t < a: s, sp = 0.5 * v / a * t * t, v * t / a
        elif t < dur_s - b: s, sp = 0.5 * v * a + v * (t - a), v
        elif t < dur_s:
            r = dur_s - t; s, sp = L - 0.5 * v / b * r * r, v * r / b
        else: s, sp = L, 0.0
        if reverse: s = L - s
        lat, lon, brg = along(info, s)
        if reverse: brg = (brg + 180) % 360
        return lat, lon, brg, sp / KN

    def snapshot(self, now_ts=None):
        import datetime
        now = self._now_local() if now_ts is None else now_ts
        out = []
        for back in (0, 1):                       # bugunun ve dunun servis gunu
            day = (now - datetime.timedelta(days=back)).replace(hour=0, minute=0, second=0, microsecond=0)
            wd = day.weekday()
            for idx, (line, mins, daytype, legs) in enumerate(self.trips):
                if not _runs_on(daytype, wd): continue
                dep = day + datetime.timedelta(minutes=mins)
                el = (now - dep).total_seconds()
                total = sum((d + w) * 60 for _, _, d, w in legs)
                if el < -self.BEFORE or el > total + self.AFTER: continue
                t = el
                for path, rev, d, w in legs:
                    D, W = d * 60, w * 60
                    if t <= D or (path, rev, d, w) == legs[-1]:
                        lat, lon, brg, sog = self._leg_state(self.paths[path], rev, D, t)
                        break
                    t -= D
                    if t <= W:
                        lat, lon, brg, sog = self._leg_state(self.paths[path], rev, D, D)
                        break
                    t -= W
                sid = 800000000 + (int(dep.timestamp() // 60) * 31 + idx) % 100000000
                out.append({"id": sid, "name": FERRY_NAMES[idx % len(FERRY_NAMES)], "cat": "passenger",
                            "len": 40 if line.startswith("HALIC") or "BESIKTAS-USK" in line or "USKUDAR-BES" in line else 72,
                            "lat": lat, "lon": lon, "sog": round(sog, 1), "cog": round(brg, 1),
                            "hdg": round(brg), "nav": 0 if sog > 0.3 else 5, "t": time.time(),
                            "line": line, "sim": True})
        return out

# ---------------------------------------------------------------- HTTP
class State:
    live = None
    sim = None
    ferries = None
    cfg = None

# duvar kagidinin kapsadigi alan
VIEW = (40.975, 28.900, 41.082, 29.075)
def in_view(sh):
    return VIEW[0] <= sh["lat"] <= VIEW[2] and VIEW[1] <= sh["lon"] <= VIEW[3]

def current():
    """mode: live = hepsi gercek, hybrid = gercek + tarifeli/simulasyon, sim = gercek veri yok"""
    cfg, live = State.cfg, State.live
    ferries = State.ferries.snapshot()
    sim = State.sim.snapshot()
    if live is None or cfg["mode"] == "sim":
        return "sim", ferries + sim, 0
    real = [x for x in live.snapshot() if in_view(x)]
    if cfg["mode"] == "live":
        return "live", real, len(real)
    out = list(real)
    real_pax = sum(1 for x in real if x.get("cat") == "passenger")
    if real_pax < 2:            # Bogaz'dan gercek vapur verisi yoksa tarifeli vapurlar
        out += ferries
    if len(real) < 5:           # gercek gemi az ise transit/demirli simulasyon
        out += sim
    mode = "live" if len(out) == len(real) else ("hybrid" if real else "sim")
    return mode, out, len(real)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] not in ("/ships.json", "/"):
            self.send_error(404)
            return
        mode, ships, nreal = current()
        body = json.dumps({"mode": mode, "time": time.time(), "count": len(ships), "real": nreal,
                           "liveTotal": len(State.live.snapshot()) if State.live else 0,
                           "liveConfigured": State.live is not None,
                           "connected": bool(State.live and State.live.connected),
                           "ships": ships}, separators=(",", ":")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

def main():
    cfg = load_config()
    State.cfg = cfg
    if cfg["mode"] != "sim" and cfg["api_key"]:
        State.live = LiveFeed(cfg)
        State.live.start()
        log("mod: canli (AISStream)")
    else:
        log("mod: simulasyon (API anahtari yok)" if not cfg["api_key"] else "mod: simulasyon")
    State.sim = Sim()
    State.sim.start()
    State.ferries = Ferries(SIM_ROUTES["ferry_paths"])
    srv = ThreadingHTTPServer(("127.0.0.1", int(cfg["port"])), Handler)
    log(f"http://127.0.0.1:{cfg['port']}/ships.json")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
