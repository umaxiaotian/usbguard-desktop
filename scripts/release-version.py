#!/usr/bin/env python3
"""Validate a stable release tag and update every packaged version."""

import re
import sys
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path


def release_version(tag):
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError("Expected a stable tag like v0.1.0")
    return tag[1:]


def main():
    version = release_version(sys.argv[1])
    root = Path(__file__).resolve().parent.parent
    for file, pattern, replacement in (
        ("pyproject.toml", r'^version = ".*"$', f'version = "{version}"'),
        ("src/usb_protection/__init__.py", r'^__version__ = ".*"$', f'__version__ = "{version}"'),
    ):
        path = root / file
        content, count = re.subn(pattern, replacement, path.read_text(), flags=re.MULTILINE)
        if count != 1:
            raise ValueError(f"Expected one version in {file}")
        path.write_text(content)
    changelog = root / "debian/changelog"
    if not changelog.read_text().startswith(f"usbguard-desktop ({version}-1)"):
        date = format_datetime(datetime.now(UTC))
        changelog.write_text(
            f"usbguard-desktop ({version}-1) unstable; urgency=medium\n\n"
            f"  * Release {version}.\n\n"
            f" -- Yuma Obata <yuma@obata.me>  {date}\n\n" + changelog.read_text()
        )
    metadata = root / "data/io.github.umaxiaotian.USBProtection.metainfo.xml"
    metadata.write_text(
        re.sub(
            r'<release version="[^"]+" date="[^"]+">',
            f'<release version="{version}" date="{datetime.now(UTC):%Y-%m-%d}">',
            metadata.read_text(),
            count=1,
        )
    )
    for path in (root / "data/man").glob("*.1"):
        path.write_text(
            re.sub(r"USB Protection \d+\.\d+\.\d+", f"USB Protection {version}", path.read_text())
        )
    print(version)


if __name__ == "__main__":
    main()
