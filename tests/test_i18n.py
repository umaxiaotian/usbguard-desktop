import gettext
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = {
    "ja": "USB プロテクション",
    "ko": "USB 보호",
    "zh_CN": "USB 保护",
    "es": "Protección USB",
}


@pytest.mark.parametrize(("language", "title"), LANGUAGES.items())
def test_catalog_is_valid_complete_and_loadable(tmp_path, language, title):
    pot = tmp_path / "messages.pot"
    source_root = ROOT / "src" if (ROOT / "src").is_dir() else ROOT / "usb_protection"
    sources = sorted(source_root.rglob("*.py"))
    subprocess.run(
        [
            "xgettext",
            "--language=Python",
            "--keyword=_",
            "--from-code=UTF-8",
            f"--output={pot}",
            *map(str, sources),
        ],
        check=True,
    )
    merged = tmp_path / f"{language}.po"
    subprocess.run(
        [
            "msgmerge",
            "--quiet",
            "--no-fuzzy-matching",
            f"--output={merged}",
            str(ROOT / "po" / f"{language}.po"),
            str(pot),
        ],
        check=True,
    )
    untranslated = subprocess.run(
        ["msgattrib", "--untranslated", "--no-obsolete", str(merged)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout
    # The catalog header is the sole empty msgid; every application string is translated.
    assert untranslated.count("\nmsgid ") == 0

    catalog = tmp_path / language / "LC_MESSAGES" / "usbguard-desktop.mo"
    catalog.parent.mkdir(parents=True)
    subprocess.run(
        ["msgfmt", "--check", "--check-format", f"--output-file={catalog}", str(merged)],
        check=True,
    )
    translation = gettext.translation("usbguard-desktop", tmp_path, [language])
    assert translation.gettext("USB Protection") == title
    assert "{name}" in translation.gettext("{name}\n{kind}\nBlocked until you choose what to do.")


def test_default_language_is_english(monkeypatch):
    monkeypatch.delenv("LANGUAGE", raising=False)
    assert (
        gettext.translation("usbguard-desktop", "/nonexistent", fallback=True).gettext(
            "USB Protection"
        )
        == "USB Protection"
    )


def test_locale_override(monkeypatch, tmp_path):
    monkeypatch.setenv("USB_PROTECTION_LOCALEDIR", os.fspath(tmp_path))
    import usb_protection.i18n as i18n

    assert i18n._locale_dir() == os.fspath(tmp_path)
