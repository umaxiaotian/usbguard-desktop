#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
repo=$(pwd)
staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT HUP INT TERM
mkdir -p "$staging/source" "$repo/dist"
tar --exclude=.git --exclude=dist --exclude=build --exclude=.pybuild \
    --exclude=.venv --exclude=__pycache__ --exclude='*.egg-info' \
    --exclude=debian/usbguard-desktop --exclude=debian/.debhelper \
    -cf - . | tar -xf - -C "$staging/source"
cd "$staging/source"
dpkg-buildpackage -us -uc -b
cp "$staging"/*.deb "$staging"/*.buildinfo "$staging"/*.changes "$repo/dist/"
