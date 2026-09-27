import os
import stat

import pytest

from usb_protection.services import bootstrap as b


def generate(stream):
    stream.write(b"allow id 1234:5678\n")


def publish(path, generator=generate, validator=lambda _: None):
    b.publish_policy(path, generator, validator, owner=os.getuid())


def test_atomic_write_and_permissions(tmp_path):
    policy = tmp_path / "rules.conf"

    def validate(temporary):
        assert not policy.exists()
        assert temporary.read_text() == "allow id 1234:5678\n"
        assert stat.S_IMODE(temporary.stat().st_mode) == 0o600

    publish(policy, validator=validate)
    assert policy.read_text() == "allow id 1234:5678\n"
    assert stat.S_IMODE(policy.stat().st_mode) == 0o600
    assert list(tmp_path.iterdir()) == [policy]


@pytest.mark.parametrize("existing", ["", "allow", "malformed"])
def test_existing_policy_never_overwritten(tmp_path, existing):
    policy = tmp_path / "rules.conf"
    policy.write_text(existing)
    with pytest.raises(b.BootstrapError):
        publish(policy)
    assert policy.read_text() == existing


def test_symlink_never_overwritten(tmp_path):
    policy = tmp_path / "rules.conf"
    policy.symlink_to(tmp_path / "absent")
    with pytest.raises(b.BootstrapError):
        publish(policy)
    assert policy.is_symlink()


def test_concurrent_policy_creation(tmp_path):
    policy = tmp_path / "rules.conf"
    with pytest.raises(b.BootstrapError):
        publish(policy, validator=lambda _: policy.write_text("administrator edit"))
    assert policy.read_text() == "administrator edit"


def test_validation_failure_cleanup(tmp_path):
    def invalid(_):
        raise b.BootstrapError("syntax error")

    with pytest.raises(b.BootstrapError):
        publish(tmp_path / "rules.conf", validator=invalid)
    assert not list(tmp_path.iterdir())


def test_empty_generation(tmp_path):
    with pytest.raises(b.BootstrapError):
        publish(tmp_path / "rules.conf", generator=lambda _: None)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("args", [[], ["initialize", "/tmp/evil"], ["exec"], ["--help"]])
def test_no_arbitrary_arguments(args):
    assert b.main(args) == 2


def test_parser_is_upstream(tmp_path, monkeypatch):
    policy = tmp_path / "rules.conf"
    policy.write_text("allow id 1234:5678\n")
    monkeypatch.setattr(b, "secure_file", lambda _: None)
    calls = []
    b.validate_policy(policy, lambda argv, **kwargs: calls.append(argv))
    assert calls == [["/usr/bin/usbguard-rule-parser", "-f", str(policy)]]
