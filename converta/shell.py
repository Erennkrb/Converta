"""Explorer context menu registration."""
import ctypes
import os
import sys
import winreg

from . import APP_NAME
from .formats import SEP, all_source_exts, group_of, menu_label, targets_for
from .paths import app_dir, asset, frozen

CLASSES = r"Software\Classes\SystemFileAssociations"
SHCNE_ASSOCCHANGED = 0x08000000
ECF_SEPARATORBEFORE = 0x20
# Explorer on current Windows 11 builds ignores per-user (HKCU) verbs here,
# so the menu goes into HKLM, which needs admin rights.
MENU_ROOT = winreg.HKEY_LOCAL_MACHINE


def launch_command():
    """Command prefix Explorer runs. Works both as script and as frozen .exe."""
    if frozen():
        return f'"{sys.executable}"'
    exe = sys.executable
    pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pythonw):
        exe = pythonw  # no console window flashing up
    return f'"{exe}" "{os.path.join(app_dir(), "main.py")}"'


def icon_path():
    return sys.executable if frozen() else asset("converta.ico")


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(args):
    """Restart this program elevated (UAC prompt) with the given arguments."""
    params = args if frozen() else [os.path.join(app_dir(), "main.py")] + args
    line = " ".join(f'"{p}"' for p in params)
    return ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, line, None, 0) > 32


def _delete_tree(root, path):
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_tree(root, f"{path}\\{sub}")
        winreg.DeleteKey(root, path)
    except FileNotFoundError:
        pass


def _refresh():
    ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, 0, None, None)


def install():
    uninstall(refresh=False)
    cmd = launch_command()
    for ext in all_source_exts():
        group = group_of("x" + ext)
        menu = f"{CLASSES}\\{ext}\\shell\\{APP_NAME}"
        with winreg.CreateKey(MENU_ROOT, menu) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path())
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
        separator_next = False
        for i, target in enumerate(targets_for(ext)):
            if target is SEP:
                separator_next = True
                continue
            sub = f"{menu}\\shell\\{i:02d}_{target}"
            with winreg.CreateKey(MENU_ROOT, sub) as key:
                winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, menu_label(group, target))
                # lift Explorer's 15-file limit for multi-selection
                winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
                if separator_next:
                    winreg.SetValueEx(key, "CommandFlags", 0, winreg.REG_DWORD,
                                      ECF_SEPARATORBEFORE)
                    separator_next = False
            with winreg.CreateKey(MENU_ROOT, sub + "\\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'{cmd} --to {target} "%1"')
    _refresh()


def uninstall(refresh=True):
    for root in (MENU_ROOT, winreg.HKEY_CURRENT_USER):  # HKCU: earlier versions
        for ext in all_source_exts():
            _delete_tree(root, f"{CLASSES}\\{ext}\\shell\\{APP_NAME}")
    if refresh:
        _refresh()
