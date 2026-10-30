"""English by default, German on German systems."""
import locale
import os
import sys

_german = None


def _detect_german():
    if sys.platform == "win32":
        import ctypes

        return ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x07
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return value.lower().startswith("de")
    try:
        return (locale.getlocale()[0] or "").lower().startswith("de")
    except ValueError:
        return False


def tr(english, german):
    global _german
    if _german is None:
        _german = _detect_german()
    return german if _german else english
