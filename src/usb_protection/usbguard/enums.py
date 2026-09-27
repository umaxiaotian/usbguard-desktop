from enum import IntEnum


class Target(IntEnum):
    ALLOW = 0
    BLOCK = 1
    REJECT = 2


class Presence(IntEnum):
    PRESENT = 0
    INSERT = 1
    UPDATE = 2
    REMOVE = 3
