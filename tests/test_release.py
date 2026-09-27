import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "release_version", Path(__file__).resolve().parents[1] / "scripts/release-version.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("tag", ["v0.1.0", "v1.20.3"])
def test_valid_tag(tag):
    assert module.release_version(tag) == tag[1:]


@pytest.mark.parametrize(
    "tag",
    [
        "0.1.0",
        "v01.2.3",
        "v1.2",
        "v1.2.3-rc1",
        "v1.2.3\n",
        "v1.2.3; echo bad",
        "v1.2.3$(id)",
        "../../etc/passwd",
    ],
)
def test_invalid_tag(tag):
    with pytest.raises(ValueError):
        module.release_version(tag)


def test_version_synchronization(tmp_path, monkeypatch):
    for directory in ("scripts", "src/usb_protection", "debian", "data/man"):
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyproject.toml").write_text('version = "0.1.0"\n')
    (tmp_path / "src/usb_protection/__init__.py").write_text('__version__ = "0.1.0"\n')
    (tmp_path / "debian/changelog").write_text(
        "usbguard-desktop (0.1.0-1) unstable; urgency=medium\n"
    )
    metadata = tmp_path / "data/io.github.umaxiaotian.USBProtection.metainfo.xml"
    metadata.write_text(
        '<releases><release version="0.1.0" date="2026-09-27"></release></releases>'
    )
    (tmp_path / "data/man/test.1").write_text("USB Protection 0.1.0")
    monkeypatch.setattr(module, "__file__", str(tmp_path / "scripts/release-version.py"))
    monkeypatch.setattr(module.sys, "argv", ["release-version.py", "v1.2.3"])
    module.main()
    assert "1.2.3" in (tmp_path / "pyproject.toml").read_text()
    assert "1.2.3" in (tmp_path / "src/usb_protection/__init__.py").read_text()
    assert (tmp_path / "debian/changelog").read_text().startswith("usbguard-desktop (1.2.3-1)")
    assert "USB Protection 1.2.3" == (tmp_path / "data/man/test.1").read_text()

    assert 'version="1.2.3"' in metadata.read_text()
