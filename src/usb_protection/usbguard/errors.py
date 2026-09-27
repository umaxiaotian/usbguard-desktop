class USBGuardError(Exception):
    """A recoverable backend error suitable for presentation."""


def friendly_error(error):
    message = str(error)
    lower = message.lower()
    if any(x in lower for x in ("auth", "denied", "cancel")):
        return USBGuardError("Permission was not granted. You can try again.")
    if any(x in lower for x in ("timeout", "timed out")):
        return USBGuardError("USB Protection did not respond in time. Please try again.")
    if any(x in lower for x in ("no such device", "device not found", "does not exist")):
        return USBGuardError("The device or rule is no longer available. Refresh and try again.")
    if any(x in lower for x in ("serviceunknown", "no owner", "no server", "disconnected")):
        return USBGuardError("USBGuard is unavailable. Check that protection is enabled.")
    return USBGuardError(message)
