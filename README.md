# Vantage for Omarchy

A native GTK4/libadwaita control panel that brings [Lenovo Vantage](https://www.lenovo.com/us/en/software/vantage)-style
hardware controls to Linux, styled to match [Omarchy](https://omarchy.org/) and driven by real
toggle switches instead of dialog menus.

This is an **Omarchy-only fork** of [niizam/vantage](https://github.com/niizam/vantage): the
installer, styling and key binding below all assume Arch Linux + Hyprland + Omarchy. It won't
try to detect or support anything else.

![Vantage running on Omarchy](images/screenshot.png)

## :rocket: What this fork changes

* Rewritten as a native GTK4/libadwaita app (the upstream project is Electron)
* Styled to match Omarchy automatically — see below
* Installer, styling and key binding assume Arch Linux + Hyprland + Omarchy; no other distro
  detection or support
* Launch from your Lenovo Smart/Vantage key, or search for it like anything else in Omarchy's menu
* `vantage-bind-key` helper to capture and (re)bind that key
* Hardware toggles run through a small privileged helper authorized by a scoped polkit policy
  (`org.vantage.helper`), so switching them on/off doesn't prompt for a password on every
  change — only Wi-Fi, touchpad and microphone (which don't need root) run unprivileged directly

The underlying hardware controls (Conservation Mode, Always-On USB, Thermal/Fan Mode, FN Key
Lock, Camera/Microphone/Touchpad/Wi-Fi switches) come from upstream
[niizam/vantage](https://github.com/niizam/vantage).

## :zap: The Smart/Vantage key

Many Lenovo laptops have a dedicated key for launching Vantage — sometimes a star or lightning
bolt icon, sometimes just the Insert key without Fn. What that key actually sends isn't
consistent across models (commonly `XF86Favorites`, but not always), so it's never hardcoded
here.

`make install` offers to bind it for you right after installing: press the key when prompted and
Vantage captures whatever it actually sends, then wires it up in
`~/.config/hypr/bindings.lua`. You can skip that prompt and set it up (or change it) whenever
you like:

```bash
vantage-bind-key            # capture a key press and (re)bind it to launch Vantage
vantage-bind-key --unbind   # remove the binding
```

## :art: Omarchy styling

Vantage always restyles itself to match Omarchy — sharp corners everywhere, and colors read live
from the current Omarchy theme (`~/.local/state/omarchy/current/theme/colors.toml`): background,
text and accent all come from there, plus light/dark mode. Switching your Omarchy theme and
reopening Vantage picks up all of it automatically.

## :computer: Installation

```bash
git clone https://github.com/yopaZH/omarchy-vantage.git
cd vantage
sudo make install
```

This installs dependencies via `pacman`, copies the app and helper into place, and offers to
bind your Smart/Vantage key. Launch "Lenovo Vantage" from Omarchy's app menu, or press your
bound key.

## :hotsprings: Uninstall

```bash
sudo make uninstall
```

Also removes the key binding set up by `vantage-bind-key`, if any.

## :warning: Requirements

Installed automatically by `sudo make install` via `pacman`:

* `python-gobject`, `gtk4`, `libadwaita` (>= 1.4, for `Adw.SwitchRow`)
* `polkit`
* `xorg-xinput`
* `networkmanager`
* `wev` (used by `vantage-bind-key` to detect key presses)
