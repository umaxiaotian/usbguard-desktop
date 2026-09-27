from test_core import FakeClient

from usb_protection.agent.notifications import NotificationRouter


def setup():
    client = FakeClient()
    sent, withdrawn = [], []
    router = NotificationRouter(client, lambda *args: sent.append(args), withdrawn.append)
    return client, router, sent, withdrawn


def test_notification_action_routes_to_backend():
    for action in ("allow-once", "always-allow"):
        client, router, sent, withdrawn = setup()
        router.offer(client.devices[0])
        router.offer(client.devices[0])
        assert len(sent) == 1
        token = sent[0][0]
        router.activate(token, action, lambda *_: None)
        assert client.calls[0][0][3] == (7, 0, action == "always-allow")
        assert withdrawn == [token]


def test_stale_notification_and_invalid_action():
    client, router, sent, _withdrawn = setup()
    router.offer(client.devices[0])
    router.activate(sent[0][0], "arbitrary", lambda *_: None)
    client.current_owner = ":1.99"
    router.activate(sent[0][0], "always-allow", lambda *_: None)
    assert not client.calls
    assert not router.pending


def test_unplug_withdraws():
    client, router, sent, withdrawn = setup()
    router.offer(client.devices[0])
    router.remove(7)
    router.activate(sent[0][0], "allow-once", lambda *_: None)
    assert withdrawn == [sent[0][0]]
    assert not client.calls


def test_reused_identifier_withdraws_old_identity():
    from usb_protection.usbguard.device import Device
    from usb_protection.usbguard.rule import Rule

    client, router, sent, withdrawn = setup()
    router.offer(client.devices[0])
    router.offer(Device(Rule.parse(7, 'block hash "different"')))
    assert len(sent) == 2
    assert withdrawn == [sent[0][0]]
    assert len(router.pending) == 1
