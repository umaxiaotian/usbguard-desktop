"""Notification decisions are bound to a bus owner and a connected device."""

import uuid


class NotificationRouter:
    def __init__(self, client, send, withdraw):
        self.client = client
        self.send = send
        self.withdraw = withdraw
        self.pending = {}
        self.in_flight = set()

    def offer(self, device):
        if device.rule.target != "block" or not device.identity or not self.client.owner:
            return
        for _token, (owner, current) in self.pending.items():
            if owner == self.client.owner and current.id == device.id:
                if current.identity == device.identity:
                    return
        token = uuid.uuid4().hex
        self.pending[token] = (self.client.owner, device)
        self.send(token, device)

    def remove(self, identifier):
        for token, (_owner, device) in tuple(self.pending.items()):
            if device.id == identifier:
                self.withdraw(token)
                self.pending.pop(token, None)

    def clear(self):
        for token in tuple(self.pending):
            self.withdraw(token)
        self.pending.clear()

    def activate(self, token, action, callback):
        if token not in self.pending or token in self.in_flight:
            return
        owner, device = self.pending[token]
        if owner != self.client.owner:
            self.clear()
            callback(None, "USB Protection restarted. Use the current device list.")
            return
        if action not in {"allow-once", "always-allow"}:
            return
        self.in_flight.add(token)

        def done(value, error):
            self.in_flight.discard(token)
            if not error:
                self.remove(device.id)
            callback(value, error)

        self.client.apply(device, action, done, owner)
