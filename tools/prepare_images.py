#!/usr/bin/env python3
"""
Isometric Istanbul ekran goruntusunden duvar kagidi gorsellerini uretir:
  1) gomulu gemileri ve dumen sularini siler  -> bosphorus.jpg
  2) sehir isikli gece surumunu olusturur     -> bosphorus_night.jpg

Kullanim:  python3 tools/prepare_images.py ekran_goruntusu.png
Gereken:   pip install opencv-python numpy

Not: Georeferans (plasmoid/contents/ui/geo.js) ve korunan bolgeler (Kiz Kulesi, Haydarpasa
mendirekleri vb.) README'de anlatilan kadraja gore ayarlidir. Farkli bir kadraj kullanirsan
geo.js icindeki H matrisini ve asagidaki koordinatlari yeniden hesaplaman gerekir.
"""
import os, sys
import cv2
import numpy as np

W_EXPECTED, H_EXPECTED = 2160, 1440

def remove_ships(src):
    img = src.copy()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h,s,v = cv2.split(hsv)
    water = ((h>=90)&(h<=115)&(s>=110)).astype(np.uint8)
    # smooth water mask a bit
    water = cv2.morphologyEx(water, cv2.MORPH_OPEN, np.ones((3,3),np.uint8))
    nonw = 1-water
    n, lab, stats, cent = cv2.connectedComponentsWithStats(nonw, 8)
    ships = np.zeros_like(water)
    H,W = water.shape
    keep=[]
    for i in range(1,n):
        x,y,w,hh,a = stats[i]
        if a > 2500: continue
        if x==0 or y==0 or x+w>=W or y+hh>=H: continue
        # must be surrounded mostly by water: check ring
        comp = (lab[y:y+hh,x:x+w]==i).astype(np.uint8)
        pad = 6
        y0,y1,x0,x1 = max(0,y-pad),min(H,y+hh+pad),max(0,x-pad),min(W,x+w+pad)
        m = np.zeros((y1-y0,x1-x0),np.uint8); m[y-y0:y-y0+hh, x-x0:x-x0+w]=comp
        ring = cv2.dilate(m,np.ones((9,9),np.uint8)) - m
        frac = water[y0:y1,x0:x1][ring>0].mean() if ring.sum() else 0
        if frac < 0.85: continue
        ships[lab==i]=1; keep.append((int(cent[i][0]),int(cent[i][1]),int(a)))
    # brighter-than-local water (wakes)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    blur = cv2.medianBlur(gray.astype(np.uint8), 31).astype(np.float32)
    wake = ((gray-blur)>10) & (water>0)
    wake = cv2.morphologyEx(wake.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2,2),np.uint8))
    # only wakes inside water away from shore
    shore = cv2.erode(water, np.ones((15,15),np.uint8))
    wake = wake & shore
    mask = cv2.dilate(((ships>0)|(wake>0)).astype(np.uint8)*255, np.ones((11,11),np.uint8))
    protect = np.zeros_like(mask)
    cv2.circle(protect,(1290,780),16,255,-1)          # Kiz Kulesi
    cv2.ellipse(protect,(388,340),(38,22),-15,0,360,255,-1)  # Halic adasi
    cv2.rectangle(protect,(1720,1340),(1830,1440),255,-1)  # Kalamis marina
    cv2.polylines(protect,[np.array([(1261,942),(1300,995),(1320,1020),(1365,1083),(1380,1098),(1418,1115)])],False,255,9)
    cv2.line(protect,(1418,1091),(1498,1140),255,9)
    mask[protect>0]=0
    out = cv2.inpaint(img, mask, 9, cv2.INPAINT_TELEA)
    return out, len(keep)


def make_night(clean):
    rng = np.random.default_rng(11)
    img = clean.astype(np.float32) / 255
    H, W = img.shape[:2]
    hsv = cv2.cvtColor((img*255).astype(np.uint8), cv2.COLOR_BGR2HSV); h, s, v = [c.astype(np.int32) for c in cv2.split(hsv)]
    water = ((h >= 88) & (h <= 118) & (s >= 90)).astype(np.uint8)
    water = cv2.morphologyEx(water, cv2.MORPH_OPEN, np.ones((5,5),np.uint8))
    water = cv2.morphologyEx(water, cv2.MORPH_CLOSE, np.ones((9,9),np.uint8)).astype(np.float32)
    land = 1 - water
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def blur(a, sg): return cv2.GaussianBlur(a, (0,0), sg)

    green = blur(((h >= 30) & (h <= 85) & (s >= 60)).astype(np.float32), 5)
    road = ((s < 45) & (v > 110) & (v < 240)).astype(np.uint8)
    # ana yollar: uzun dogrusal yapilar
    wide = cv2.morphologyEx(road, cv2.MORPH_OPEN, np.ones((7,7),np.uint8))
    road = road & (1 - cv2.dilate(wide, np.ones((3,3),np.uint8)))
    major = np.zeros_like(road)
    for ang in range(0, 180, 15):
        k = np.zeros((31,31), np.uint8); c = 15
        dx, dy = np.cos(np.radians(ang))*15, np.sin(np.radians(ang))*15
        cv2.line(k, (int(c-dx), int(c-dy)), (int(c+dx), int(c+dy)), 1, 1)
        major |= cv2.morphologyEx(road, cv2.MORPH_OPEN, k)
    major = major.astype(np.float32)
    roof = (((h <= 22) | (h >= 170)) & (s > 70)).astype(np.float32)
    urban = blur(roof, 4)
    # kumelenme: dusuk frekansli gurultu (mahalleler farkli parlaklikta)
    n1 = blur(rng.random((H, W)).astype(np.float32), 45); n1 = (n1 - n1.min()) / (n1.max() - n1.min())
    n2 = blur(rng.random((H, W)).astype(np.float32), 12); n2 = (n2 - n2.min()) / (n2.max() - n2.min())
    cluster = 0.45 + 0.9 * n1 * (0.7 + 0.6 * n2)

    dark = np.clip(1 - green * 1.5, 0, 1) * land
    detail = np.clip(gray * 1.4, 0, 1) ** 1.6     # catilar/sokaklar dokusu

    # isik maskeleri: top-hat ile ince parlak yapilar (sokaklar, caddeler) -> sokak lambasi agi
    th = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13,13)))
    greyish = np.clip(1 - s / 60.0, 0, 1)
    streets = np.clip(th * (0.35 + 0.65 * greyish) * 5.0, 0, 1)
    streets = blur(streets, 0.7) ** 2.2
    cl = (0.25 + 1.1 * n1 * (0.6 + 0.8 * n2)) ** 1.6
    m = streets * dark * cl
    shore = (cv2.dilate(water.astype(np.uint8), np.ones((5,5),np.uint8)) - water).astype(np.float32) * land
    m_shore = blur(shore, 1) * 0.35 * cl
    warm   = np.array([0.62, 0.86, 1.00], np.float32)
    sodium = np.array([0.08, 0.42, 1.00], np.float32)
    mixc = np.clip(0.35 + greyish * 0.5 + 0.4 * (n2 - 0.5), 0, 1)[...,None]
    col = mixc * sodium + (1 - mixc) * warm
    E = m[...,None] * col * 1.35 + m_shore[...,None] * warm
    # parlak noktalar: sokak isiginin yerel tepe noktalari
    mx = cv2.dilate(streets, np.ones((7,7),np.uint8))
    peaks = (streets >= mx) & (streets > 0.5) & (dark > 0.5) & (rng.random((H, W)) < 0.6 * np.clip(cl, 0, 1))
    E[peaks] += np.array([0.55, 0.85, 1.0]) * 1.4
    # pencere noktaciklari (az)
    pts = (rng.random((H, W)) < urban * dark * 0.004 * cl)
    E[pts] += np.array([0.7, 0.85, 1.0]) * rng.uniform(0.5, 1, (pts.sum(), 1))

    hi = np.clip(E - 0.35, 0, None)
    glow = blur(E, 1.5) * 0.35 + blur(hi, 6) * 1.2 + blur(E, 18) * 0.35

    # gece tabani: koyu, mavimsi
    base = img * np.array([0.075, 0.055, 0.045], np.float32) + np.array([0.03, 0.015, 0.008], np.float32)
    base[water > 0] = img[water > 0] * np.array([0.19, 0.11, 0.055]) + np.array([0.04, 0.02, 0.008])
    out = base + E * 0.9 + glow * np.where(water[...,None] > 0, 0.55, 0.45)
    # hafif ton egrisi
    out = 1 - np.exp(-out * 1.35)
    out = np.clip(out, 0, 1)
    return (out * 255).astype(np.uint8)


def main():
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(1)
    src = cv2.imread(sys.argv[1])
    if src is None:
        sys.exit("gorsel okunamadi: " + sys.argv[1])
    h, w = src.shape[:2]
    if (w, h) != (W_EXPECTED, H_EXPECTED):
        if abs(w / h - 1.5) > 0.01:
            sys.exit(f"gorsel {w}x{h}; beklenen {W_EXPECTED}x{H_EXPECTED} (3:2) kadraj")
        print(f"uyari: {w}x{h} -> {W_EXPECTED}x{H_EXPECTED} olcekleniyor")
        src = cv2.resize(src, (W_EXPECTED, H_EXPECTED), interpolation=cv2.INTER_AREA)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plasmoid", "contents", "images")
    clean, n = remove_ships(src)
    print(f"{n} gemi silindi")
    cv2.imwrite(os.path.join(out_dir, "bosphorus.jpg"), clean, [cv2.IMWRITE_JPEG_QUALITY, 93])
    print("gece gorseli uretiliyor...")
    cv2.imwrite(os.path.join(out_dir, "bosphorus_night.jpg"), make_night(clean), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("tamam ->", os.path.normpath(out_dir))

if __name__ == "__main__":
    main()
