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
