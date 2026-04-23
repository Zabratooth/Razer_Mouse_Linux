## 🔀 Fork Notes – Zabratooth/Razer_Mouse_Linux

> This is a fork of [lostallmymoney/Razer_Mouse_Linux](https://github.com/lostallmymoney/Razer_Mouse_Linux), patched for stability on **KDE Plasma (Wayland)** with a **Razer Basilisk V3** and **Razer Ornata V3 X**.

### ✅ Tested Environment

| Component | Details |
|---|---|
| OS | Nobara 43 (Fedora-based) |
| Desktop | KDE Plasma 6, Wayland |
| Mouse | Razer Basilisk V3 |
| Keyboard | Razer Ornata V3 X |
| CPU | AMD Ryzen (AM5) |
| GPU | NVIDIA RTX 4070 |

---

### 🛠️ Patches Applied

#### 1. `nagaDotoolLib.hpp` – Exception safety on Wayland
All `throw` statements replaced with `return` to prevent crashes when dotool pipe operations fail silently under Wayland.

#### 2. `nagaWayland.cpp` (line ~925) – Same fix
One remaining `throw` replaced with `return` for consistent error handling.

#### 3. `nagaServerCatcher.sh` – Wayland compatibility
- `killall nagaDotoold` commented out (causes issues on some Wayland setups)
- Detection logic patched with `if true` to force Wayland mode reliably

#### 4. `notify-send` – Replaced with dummy
`notify-send` was causing crashes. Replaced with a no-op dummy script at `/usr/local/bin/notify-send` to suppress notifications without breaking execution.

#### 5. KDE Klipper – Primary Selection disabled
Klipper's "Primary Selection" feature interfered with clipboard operations triggered by the daemon. Disabled in KDE settings.

#### 6. Compile with `g++ -std=c++20`
`nagaWayland` requires C++20. Build command updated accordingly.

---

### 📦 Nobara/Fedora Install

The upstream installer assumes Debian/Ubuntu (`apt`). For Nobara/Fedora use the included `setup_nobara.sh` or install dependencies manually:

```bash
sudo dnf install g++ golang dotool dbus-devel
```

Then compile and install:

```bash
sh install.sh wayland
```

---

### 🔧 Extra Scripts

#### `toggle_keys.sh`
Toggles mouse buttons 13 and 14 between placeholder keys (`t`/`u`) and actual game keys (`F9`/`F10`). Useful for games where loop macros need to be enabled/disabled on demand.

```bash
~/toggle_keys.sh
```

---

### 🖥️ Bonus Tool: `keypress_feed.py`

A standalone Python/GTK3 keypress overlay included in this repo as an optional companion tool. Originally built to monitor Razer mouse button events (F9/F10 macros) during gameplay.

**Features:**
- Live keypress feed – entries appear at the bottom and scroll upward
- Larger input line at the bottom (separated by a divider)
- Repeat counter badge (black box, white number) for repeated keypresses
- Smooth slide-up animation when entries disappear
- White background, clean monospace font

**Dependencies:**
```bash
sudo dnf install python3-gobject python3-evdev gtk3
```

**Run:**
```bash
python3 keypress_feed.py
```

**Autostart / Desktop shortcut:**

Create `~/.local/share/applications/keyfeed.desktop`:
```ini
[Desktop Entry]
Type=Application
Name=Key Feed
Exec=python3 /home/david/keypress_feed.py
Icon=input-keyboard
Terminal=false
Categories=Utility;
```

Then copy to desktop:
```bash
cp ~/.local/share/applications/keyfeed.desktop ~/Schreibtisch/
chmod +x ~/Schreibtisch/keyfeed.desktop
```

**Note:** The tool reads from `/dev/input/` directly via `evdev`. It does **not** grab the device exclusively, so other applications (games, etc.) continue to receive input normally.

---

### 📁 Config Location

| File | Path |
|---|---|
| Key map | `~/.naga/keyMapWayland.txt` |
| Autostart | `~/.config/autostart/naga.desktop` |
| Dotool service | `~/.config/systemd/user/dotoold.service` |
| Install path | `/usr/local/bin/Naga_Linux/` |

