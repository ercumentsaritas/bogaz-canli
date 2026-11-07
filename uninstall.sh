#!/usr/bin/env bash
set -uo pipefail
systemctl --user disable --now bogaz-canli.service 2>/dev/null
rm -f ~/.config/systemd/user/bogaz-canli.service
systemctl --user daemon-reload
rm -rf ~/.local/share/bogaz-canli
kpackagetool6 -t Plasma/Wallpaper -r com.ercument.bogazcanli 2>/dev/null
echo "Kaldirildi. (Ayarlar korundu: ~/.config/bogaz-canli/ ; duvar kagidini elle degistirmeyi unutma)"
