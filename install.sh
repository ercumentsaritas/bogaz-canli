#!/usr/bin/env bash
# Bogaz Canli kurulumu (Fedora KDE / Plasma 6)
# Kullanim: ./install.sh            -> kur ve duvar kagidi olarak ayarla
#           ./install.sh --no-set   -> kur, duvar kagidini degistirme
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ID="com.ercument.bogazcanli"

IMG="$DIR/plasmoid/contents/images"
if [ ! -f "$IMG/bosphorus.jpg" ] || [ ! -f "$IMG/bosphorus_night.jpg" ]; then
    echo "!! Duvar kagidi gorselleri yok. Once README'deki 'Gorseli hazirla' adimini uygula:"
    echo "   python3 tools/prepare_images.py <isometric-istanbul-ekran-goruntusu.png>"
    exit 1
fi

echo "==> AIS servisi kuruluyor"
mkdir -p ~/.local/share/bogaz-canli ~/.config/bogaz-canli ~/.config/systemd/user
install -m 755 "$DIR/service/bogaz_ais.py" ~/.local/share/bogaz-canli/bogaz_ais.py
if [ ! -f ~/.config/bogaz-canli/config.json ]; then
    cp "$DIR/service/config.example.json" ~/.config/bogaz-canli/config.json
    echo "    ayar dosyasi: ~/.config/bogaz-canli/config.json"
fi
cp "$DIR/service/bogaz-canli.service" ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable bogaz-canli.service >/dev/null
systemctl --user restart bogaz-canli.service

echo "==> Plasma duvar kagidi eklentisi kuruluyor"
if kpackagetool6 -t Plasma/Wallpaper -s "$ID" >/dev/null 2>&1; then
    kpackagetool6 -t Plasma/Wallpaper -u "$DIR/plasmoid"
else
    kpackagetool6 -t Plasma/Wallpaper -i "$DIR/plasmoid"
fi

if [ "${1:-}" != "--no-set" ]; then
    echo "==> Tum masaustlerinde duvar kagidi olarak ayarlaniyor"
    QDBUS="$(command -v qdbus6 || command -v qdbus-qt6 || command -v qdbus || true)"
    if [ -n "$QDBUS" ]; then
        "$QDBUS" org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
          "desktops().forEach(function(d){ d.wallpaperPlugin='$ID'; d.currentConfigGroup=['Wallpaper','$ID','General']; });" \
          && echo "    tamam" || echo "    otomatik ayarlanamadi; Sag tik > Masaustu ve Duvar Kagidi Yapilandir > 'Bogaz Canli'"
    else
        echo "    qdbus bulunamadi; Sag tik > Masaustu ve Duvar Kagidi Yapilandir > 'Bogaz Canli'"
    fi
fi

sleep 1
if curl -fsS http://127.0.0.1:8765/ships.json >/dev/null 2>&1; then
    echo "==> Servis calisiyor: http://127.0.0.1:8765/ships.json"
else
    echo "!!  Servis yanit vermedi. Kontrol: journalctl --user -u bogaz-canli -n 30"
fi
if ! python3 -c "import websockets" 2>/dev/null; then
    echo
    echo "Not: Canli AIS modu icin 'websockets' gerekli:  sudo dnf install python3-websockets"
fi
echo
echo "Eklentiyi guncelledikten sonra degisiklik gorunmezse:  systemctl --user restart plasma-plasmashell"
