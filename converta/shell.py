"""File manager integration for the current platform."""
import sys

if sys.platform == "win32":
    from .shell_windows import install, is_admin, relaunch_as_admin, uninstall

    def needs_nautilus_python():
        return False
else:
    from .shell_linux import (install, is_admin, needs_nautilus_python, relaunch_as_admin,
                              uninstall)

__all__ = ["install", "is_admin", "needs_nautilus_python", "relaunch_as_admin", "uninstall"]
