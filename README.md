<div align="center">

<img src="assets/icon.png" width="120" alt="AutoMacro icon">

# AutoMacro

**Configurable hotkey macro automation for any application.**

Build a sequence of key taps, hotkey combos and typed text, point it at any
open app, set your cooldowns, and run it with a single global hotkey.

</div>

---

## What it does

AutoMacro is a small desktop app that automatically presses keys, fires
hotkey combinations, and types text into **any application you choose**. You
pick a target window, arrange a sequence of steps, dial in the timing, and
start/stop it from anywhere with a global hotkey.

- 🎯 **Target any app** — pick from a live list of open windows, or type part
  of a window title. AutoMacro focuses that window before sending input.
- ⌨️ **Four step types** — single **key taps** (`enter`, `f5`, `a`),
  **hotkey combos** (`ctrl+shift+esc`), **typed text**, and explicit
  **waits**.
- ⏱️ **Fully configurable cooldowns** — start delay, per-step delay,
  between-loop cooldown, loop count (finite or infinite), and optional
  timing **jitter** for more natural pacing.
- 🔁 **Multiple saved macros** — create, duplicate, rename and switch between
  as many macro profiles as you like; everything autosaves.
- 🖲️ **Global start/stop + emergency stop** hotkeys that work even when
  another app has focus.
- 🎨 **Modern UI** with light / dark / system themes.
- 📦 **Ships as a single pinnable app** — build one file you can pin to the
  taskbar (Windows), Dock (macOS) or app menu (Linux).

Runs on **Windows, macOS and Linux**.

---

## Quick start (run from source)

You need **Python 3.9+**.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run it
python run.py
```

> On **Linux** you also need Tk (`sudo apt install python3-tk`) and, for
> window targeting, `sudo apt install wmctrl xdotool`.

Check your environment at any time:

```bash
python run.py --doctor
```

This prints whether keyboard input, window targeting and global hotkeys are
available, and why if not.

---

## Build the pinnable app 📌

This turns AutoMacro into **one standalone file that reads and launches like a
normal application** — no Python required to run it afterwards.

### Windows
Double-click **`build\build_windows.bat`** (or run it in a terminal).
When it finishes you'll have a single file:

```
dist\AutoMacro.exe
```

Move it somewhere permanent (e.g. your Documents), double-click to run, then
right-click its taskbar icon → **Pin to taskbar**. Because it isn't
code-signed, Windows may warn or block it on first run — see
**[Windows security prompts](#windows-security-prompts-smartscreen--smart-app-control)** below.

### macOS
```bash
bash build/build_macos.sh
```
Produces **`dist/AutoMacro.app`**. Drag it into `/Applications` and keep it in
the Dock. On first run, grant Accessibility permission in
**System Settings → Privacy & Security → Accessibility** (this is what lets it
send keystrokes).

### Linux
```bash
bash build/build_linux.sh
```
Produces **`dist/AutoMacro`**. To pin it to your applications menu, edit and
install the provided launcher:

```bash
sudo mkdir -p /opt/AutoMacro
sudo cp dist/AutoMacro /opt/AutoMacro/AutoMacro     # or wherever you like
sudo cp assets/icon.png /opt/AutoMacro/icon.png
cp build/AutoMacro.desktop ~/.local/share/applications/AutoMacro.desktop
# edit the Exec= / Icon= paths in that file to match, then it appears in your menu
```

---

## Windows security prompts (SmartScreen / Smart App Control)

The app isn't signed with a commercial code-signing certificate, so Windows
may warn about it. There are **two different** Windows features to know about:

| Feature | What you see | How to proceed |
|--------|--------------|----------------|
| **SmartScreen** | "Windows protected your PC" dialog | Click **More info → Run anyway**. One time. |
| **Smart App Control (SAC)** | App is blocked with *no* "run anyway" | SAC only allows signed/known apps — see below. |

**Smart App Control** is stricter and can't be bypassed per-app. If it's on
and blocking AutoMacro, you have three options:

1. **Turn Smart App Control off** — Windows Security → *App & browser control*
   → *Smart App Control settings* → **Off**. (Note: once off it can't be
   turned back on without reinstalling Windows.)
2. **Sign it yourself for your own PC** — run, as administrator:
   ```powershell
   powershell -ExecutionPolicy Bypass -File build\sign_windows_local.ps1 -ExePath "C:\path\to\AutoMacro\AutoMacro.exe"
   ```
   This clears the SmartScreen warning on your machine. (It does **not**
   satisfy SAC, which only trusts Microsoft-known certificates.)
3. **Sign with a real certificate** — see below. This is the only way to
   clear SAC everywhere.

### Windows code signing (for distribution)

The build workflow (`.github/workflows/build.yml`) will automatically sign the
Windows `.exe` **if** you add two repository secrets:

- `WIN_CERT_PFX_BASE64` — your code-signing certificate (`.pfx`) as base64
  (`certutil -encode cert.pfx cert.txt`, or `[Convert]::ToBase64String(...)`).
- `WIN_CERT_PASSWORD` — the certificate's password.

With those present, CI signs `AutoMacro.exe` before packaging. A certificate
from a trusted CA (an **EV** certificate gives immediate SmartScreen/SAC
reputation) is what lets the download run cleanly on other people's machines.
Without the secrets, the signing step is skipped and the build is unsigned.

---

## Using it

1. **Name your macro** at the top.
2. **Pick the target app** — click **⟳ Refresh** to load open windows, then
   choose one from the dropdown (or type part of its title). Leave it empty to
   send to whatever window is focused.
   - *Match*: how the title is compared (Contains / Exact / Starts with / Regex).
   - *Focus target before running*: brings the app to the front first.
   - *Only while target is focused*: a safety gate — input is sent **only**
     while that app is focused, so stray keys never leak elsewhere.
3. **Add steps** with **＋ Add step**. For each step choose:
   - **Key tap** — one key, e.g. `enter`, `f5`, `space`, `a`
   - **Hotkey** — a combo, e.g. `ctrl+c`, `ctrl+shift+esc`, `alt+f4`
   - **Type text** — types the text you enter
   - **Mouse** — a mouse action at the current cursor position: `left`,
     `right`, `middle`, `double` (double-click), `scroll_up`, `scroll_down`,
     or `left_down` / `left_up` (press-and-hold, then release)
   - **Wait** — pauses for the given milliseconds
   - plus a per-step **delay** (ms) and a **repeat** count.
   Reorder with ▲▼, remove with ✕, and un-tick a step to disable it.
4. **Set cooldowns & timing**:
   - **Start delay** — grace period before the first run (switch to your app).
   - **Loop cooldown** — wait between full repeats.
   - **Loops** — how many times to run the whole sequence (`0` = infinite).
   - **Timing jitter** — randomises every delay by ± the chosen percentage.
5. **Choose your hotkeys** — a **start/stop** hotkey (default `f6`) and an
   **emergency stop** (default `esc`). These work globally.
6. Press **▶ Start** (or your start/stop hotkey). Press it again, the
   emergency-stop key, or close the window to stop.

Everything you change is saved automatically.

### Key names

Modifiers: `ctrl`, `alt`, `shift`, `cmd` (aliases like `control`, `win`,
`super`, `option` work too).

Named keys: `enter`, `esc`, `tab`, `space`, `backspace`, `delete`, `insert`,
`home`, `end`, `page_up`, `page_down`, `up`, `down`, `left`, `right`,
`caps_lock`, `print_screen`, `f1`–`f24`, plus media keys
(`media_play_pause`, `media_volume_up`, …). Any single character
(`a`, `7`, `/`) is also a valid key. Names are case-insensitive and spaces,
dashes or underscores are interchangeable (`Page Up` = `page_up`).

---

## Where settings are stored

A single JSON file in your user config directory:

| OS      | Path |
|---------|------|
| Windows | `%APPDATA%\AutoMacro\config.json` |
| macOS   | `~/Library/Application Support/AutoMacro/config.json` |
| Linux   | `~/.config/AutoMacro/config.json` |

Run `python run.py --doctor` to see the exact path on your machine.

---

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| Keys don't reach the target app | Make sure the correct window is selected and **Focus target before running** is on. Some apps must be run at the same privilege level (e.g. run AutoMacro as admin for an admin app on Windows). |
| Nothing happens on macOS | Grant **Accessibility** permission (System Settings → Privacy & Security → Accessibility) and relaunch. |
| Target list is empty on Linux | Install `wmctrl`/`xdotool`. Window targeting needs X11; pure Wayland sessions are limited by design. |
| Global hotkey doesn't fire | Another app may have grabbed it — pick a different key, e.g. `f8`. |
| Want a full report | `python run.py --doctor` |

---

## Development

```bash
pip install -r requirements.txt
pip install pytest
python -m pytest        # 90+ tests covering the engine, parsing and config
```

The codebase is layered so the core is dependency-free and testable headless:

```
src/automacro/
├── models.py        # macros / steps / config (serializable dataclasses)
├── keyspec.py       # key + hotkey parsing / validation
├── engine.py        # threaded execution engine with all cooldowns
├── config.py        # atomic JSON load/save
├── hotkeys.py       # global start/stop + panic hotkeys (pynput)
├── backends/        # input + window targeting, per OS, behind interfaces
├── ui/              # customtkinter interface
└── app.py           # CLI + GUI entry point
```

---

## Responsible use

AutoMacro is a general-purpose automation tool. Please use it in line with the
terms of service of any application or online service you point it at — some
games and platforms prohibit automation. You are responsible for how you use
it.

## License

[MIT](LICENSE) © 2026 kyluua
