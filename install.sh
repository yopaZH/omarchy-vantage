#!/bin/bash
# Installs Vantage's dependencies. This fork targets Omarchy (Arch Linux +
# Hyprland) only, so it goes straight to pacman rather than detecting a
# distro/package manager.
set -euo pipefail

PACKAGES=(python-gobject gtk4 libadwaita polkit xorg-xinput networkmanager wev)

command -v pacman &>/dev/null || {
    echo "pacman not found - this fork targets Omarchy (Arch Linux + Hyprland)." >&2
    exit 1
}

echo "Installing dependencies: ${PACKAGES[*]}"
pacman -Qi "${PACKAGES[@]}" &>/dev/null || sudo pacman -S --needed "${PACKAGES[@]}"

echo "Dependencies installed."
