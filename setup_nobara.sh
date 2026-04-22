#!/bin/bash
# =============================================================================
# setup_nobara.sh
# Razer_Mouse_Linux – Nobara/KDE Wayland Setup Script
# Getestet mit: Nobara 43, KDE Plasma, Wayland, Basilisk V3
# =============================================================================

set -e

REPO_DIR="$HOME/Razer_Mouse_Linux"
INSTALL_DIR="/usr/local/bin/Naga_Linux"
DOTOOL_DIR="$HOME/dotool"

echo "======================================================"
echo " Razer Mouse Linux – Nobara/KDE Wayland Setup"
echo "======================================================"

# ------------------------------------------------------------------------------
# 1. Abhängigkeiten installieren
# ------------------------------------------------------------------------------
echo ""
echo "[1/8] Installiere Abhängigkeiten..."
sudo dnf install -y \
    gcc-c++ \
    nano \
    polkit \
    procps \
    wget \
    dbus-x11 \
    curl \
    dbus-devel \
    golang \
    libX11-devel \
    xdotool \
    xinput \
    libXtst-devel \
    libXmu-devel \
    pkgconf-pkg-config \
    libxkbcommon-devel \
    git \
    unzip \
    xsel \
    wl-clipboard

# ------------------------------------------------------------------------------
# 2. razerInputGroup erstellen und User hinzufügen
# ------------------------------------------------------------------------------
echo ""
echo "[2/8] Erstelle razerInputGroup..."
sudo groupadd razerInputGroup 2>/dev/null || echo "Gruppe existiert bereits."
sudo usermod -aG razerInputGroup "$USER"
sudo usermod -aG input "$USER"

# ------------------------------------------------------------------------------
# 3. Repo klonen (falls nicht vorhanden)
# ------------------------------------------------------------------------------
echo ""
echo "[3/8] Klone Repository..."
if [ ! -d "$REPO_DIR" ]; then
    git clone https://github.com/Zabratooth/Razer_Mouse_Linux.git "$REPO_DIR"
else
    echo "Repo bereits vorhanden, überspringe Clone."
fi

# ------------------------------------------------------------------------------
# 4. dotool bauen und installieren
# ------------------------------------------------------------------------------
echo ""
echo "[4/8] Baue dotool..."
if [ ! -d "$DOTOOL_DIR" ]; then
    git clone https://git.sr.ht/~geb/dotool "$DOTOOL_DIR"
fi
cd "$DOTOOL_DIR"
./build.sh && sudo ./build.sh install
sudo udevadm control --reload && sudo udevadm trigger

# ------------------------------------------------------------------------------
# 5. nagaWayland kompilieren
# ------------------------------------------------------------------------------
echo ""
echo "[5/8] Kompiliere nagaWayland..."
cd "$REPO_DIR"
g++ -std=c++20 -o ~/nagaWayland src/nagaWayland.cpp \
    $(pkg-config --cflags --libs dbus-1) -lpthread

# Install-Script ausführen (erstellt Verzeichnisse und Symlinks)
sh src/_installWayland.sh

# Kompiliertes Binary kopieren
sudo cp ~/nagaWayland "$INSTALL_DIR/nagaWayland"
sudo chmod +x "$INSTALL_DIR/nagaWayland"
rm ~/nagaWayland

# PATH sicherstellen
if ! grep -q "/usr/local/bin" ~/.bashrc; then
    echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
fi

# ------------------------------------------------------------------------------
# 6. nagaServerCatcher.sh patchen (Wayland fix)
# ------------------------------------------------------------------------------
echo ""
echo "[6/8] Patche nagaServerCatcher.sh..."
sudo cp "$REPO_DIR/src/nagaServerCatcher.sh" "$INSTALL_DIR/nagaServerCatcher.sh"

# notify-send dummy (verhindert DBus-Crash)
if [ -f /usr/bin/notify-send ] && [ ! -f /usr/bin/notify-send.bak ]; then
    sudo mv /usr/bin/notify-send /usr/bin/notify-send.bak
    echo '#!/bin/sh' | sudo tee /usr/bin/notify-send > /dev/null
    echo 'exit 0' | sudo tee -a /usr/bin/notify-send > /dev/null
    sudo chmod +x /usr/bin/notify-send
fi

# ------------------------------------------------------------------------------
# 7. dotoold User-Service einrichten
# ------------------------------------------------------------------------------
echo ""
echo "[7/8] Richte dotoold Service ein..."
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/dotoold.service << 'EOF'
[Unit]
Description=dotoold daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/local/bin/dotoold
Restart=always
Environment="DOTOOL_PIPE=/run/.nagaProtected/nagadotool-pipe"

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable dotoold

# ------------------------------------------------------------------------------
# 8. KDE Autostart einrichten (statt systemd-Service)
# ------------------------------------------------------------------------------
echo ""
echo "[8/8] Richte KDE Autostart ein..."
mkdir -p ~/.config/autostart

cat > ~/.config/autostart/naga.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Naga Mouse Daemon
Exec=bash -c 'sleep 5 && /usr/local/bin/Naga_Linux/nagaServerCatcher.sh'
Hidden=false
NoDisplay=false
X-KDE-autostart-phase=2
EOF

# Klipper Primary Selection deaktivieren
kwriteconfig6 --file klipperrc --group General --key KeepClipboardContents false 2>/dev/null || true
kwriteconfig6 --file klipperrc --group General --key SyncClipboards false 2>/dev/null || true
kwriteconfig6 --file kwinrc --group Wayland --key EnablePrimarySelection false 2>/dev/null || true

# ------------------------------------------------------------------------------
# Fertig
# ------------------------------------------------------------------------------
echo ""
echo "======================================================"
echo " Setup abgeschlossen!"
echo "======================================================"
echo ""
echo " WICHTIG: Bitte jetzt neu einloggen oder rebooten."
echo " Danach:"
echo "   naga edit   – Tasten konfigurieren"
echo "   naga debug  – Logs anzeigen"
echo ""
echo " keyMap liegt unter: ~/.naga/keyMapWayland.txt"
echo "======================================================"
