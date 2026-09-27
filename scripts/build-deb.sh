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
# actions/setup-python prepends a hosted Python to PATH. Debian's pybuild and
# APT-installed modules must use the distribution interpreter as one coherent
# toolchain, so isolate this build from virtualenv/hosted Python shims.
PATH=/usr/sbin:/usr/bin:/sbin:/bin dpkg-buildpackage -us -uc -b
cp "$staging"/*.deb "$staging"/*.buildinfo "$staging"/*.changes "$repo/dist/"
