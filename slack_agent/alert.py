import sys

from . import config


def play_alert():
    """Play a loud alarm tone so whoever's near this machine notices
    something that needs a human. Windows-only, stdlib winsound - no
    install, no C extension. Beep() drives the hardware tone directly
    rather than an OS "program sound", so it isn't subject to the sound
    scheme/volume-mixer settings that can mute MessageBeep. Never lets a
    sound failure block the actual Slack notification - that's the real
    mechanism, this is a bonus."""
    if not config.SOUND_ALERT_ENABLED or sys.platform != "win32":
        return
    try:
        import winsound

        for _ in range(4):
            winsound.Beep(1200, 150)
            winsound.Beep(800, 150)
    except Exception:
        pass
