"""Small Tk windows: progress for slow conversions, frame and format pickers."""
import os
import sys
import threading

from PIL import Image

from . import APP_NAME
from .formats import LABELS, group_of, menu_label, targets_for, SEP
from .i18n import tr
from .paths import asset

PREVIEW_MAX = (640, 400)


def has_display():
    """False on a plain terminal or server, where Tk can't open any window."""
    if sys.platform == "win32":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def message(text, error=False):
    if sys.platform == "win32":
        import ctypes

        flags = 0x10 if error else 0x40  # MB_ICONERROR / MB_ICONINFORMATION
        ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, flags | 0x10000)  # MB_SETFOREGROUND
        return
    if has_display():
        try:
            from tkinter import messagebox

            root = _new_root(APP_NAME)
            root.withdraw()
            (messagebox.showerror if error else messagebox.showinfo)(APP_NAME, text, parent=root)
            root.destroy()
            return
        except Exception:
            pass
    print(text, file=sys.stderr if error else sys.stdout)


def _new_root(title):
    import tkinter as tk
    from tkinter import ttk

    if sys.platform == "win32":
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    root.title(title)
    root.resizable(False, False)
    try:
        if sys.platform == "win32":
            root.iconbitmap(asset("converta.ico"))
        else:
            root.iconphoto(True, tk.PhotoImage(file=asset("converta.png")))
            ttk.Style(root).theme_use("clam")  # Tk's default Linux theme looks dated
    except Exception:
        pass
    return root


def _bold(root):
    from tkinter import font

    bold = font.nametofont("TkDefaultFont", root=root).copy()
    bold.configure(weight="bold", size=abs(bold.cget("size")) + 1)
    return bold


def _center(root):
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    root.lift()
    try:
        root.attributes("-topmost", True)
        root.after(300, lambda: root.attributes("-topmost", False))
    except Exception:
        pass  # not every Linux window manager supports it
    root.focus_force()


# --- progress ----------------------------------------------------------------

class Cancelled(Exception):
    pass


def run_jobs(jobs, show_window):
    """Run [(file, fn(progress))] one after another. Returns a list of error lines."""
    errors = []

    def run_one(path, fn, progress):
        try:
            fn(progress)
        except Cancelled:
            raise
        except Exception as e:
            errors.append(f"{os.path.basename(path)}: {e}")

    if not show_window or not has_display():
        for path, fn in jobs:
            run_one(path, fn, lambda fraction, text=None: None)
        return errors

    from tkinter import ttk

    root = _new_root(APP_NAME)
    frame = ttk.Frame(root, padding=16)
    frame.pack()
    title = ttk.Label(frame, font=_bold(root), width=48)
    title.pack(anchor="w")
    name = ttk.Label(frame, foreground="gray", width=48)
    name.pack(anchor="w", pady=(2, 10))
    bar = ttk.Progressbar(frame, length=380, maximum=1000)
    bar.pack()
    state = {"index": 0, "fraction": None, "text": None, "done": False, "cancel": False}

    def cancel():
        state["cancel"] = True
        cancel_button.state(["disabled"])
        title.configure(text=tr("Cancelling…", "Wird abgebrochen…"))

    cancel_button = ttk.Button(frame, text=tr("Cancel", "Abbrechen"), command=cancel)
    cancel_button.pack(anchor="e", pady=(12, 0))
    root.protocol("WM_DELETE_WINDOW", cancel)

    def progress(fraction, text=None):
        if state["cancel"]:
            raise Cancelled()
        state["fraction"] = fraction
        state["text"] = text

    def worker():
        try:
            for i, (path, fn) in enumerate(jobs):
                if state["cancel"]:
                    break
                state.update(index=i, fraction=None, text=None)
                run_one(path, fn, progress)
        except Cancelled:
            pass
        state["done"] = True

    def poll():
        if state["done"]:
            bar.stop()
            root.destroy()
            return
        if not state["cancel"]:
            i = state["index"]
            if state["text"]:
                title.configure(text=state["text"])
            else:
                title.configure(text=tr("Converting…", "Wird umgewandelt…") if len(jobs) == 1
                                else tr(f"Converting file {i + 1} of {len(jobs)}…",
                                        f"Datei {i + 1} von {len(jobs)} wird umgewandelt…"))
            name.configure(text=os.path.basename(jobs[i][0]))
        if state["fraction"] is None:
            if str(bar["mode"]) != "indeterminate":
                bar.configure(mode="indeterminate")
                bar.start(12)
        else:
            if str(bar["mode"]) != "determinate":
                bar.stop()
                bar.configure(mode="determinate")
            bar["value"] = state["fraction"] * 1000
        root.after(100, poll)

    def reveal():
        # quick jobs finish before this fires, so no window flashes up
        if not state["done"]:
            root.deiconify()
            _center(root)

    root.withdraw()
    threading.Thread(target=worker, daemon=True).start()
    poll()
    root.after(500, reveal)
    root.mainloop()
    return errors


# --- frame picker --------------------------------------------------------------

class AnimationFrames:
    def __init__(self, path):
        self.img = Image.open(path)
        self.count = self.img.n_frames

    def frame(self, i):
        self.img.seek(i)
        return self.img.convert("RGBA")

    def describe(self, i):
        return tr(f"Frame {i + 1} of {self.count}", f"Frame {i + 1} von {self.count}")


class VideoFrames:
    STEP = 0.1  # seconds per slider step

    def __init__(self, path):
        from . import media

        self.path = path
        self.media = media
        self.length = media.duration(path) or 0
        self.count = max(1, int(self.length / self.STEP))

    def frame(self, i):
        return self.media.grab_frame(self.path, i * self.STEP)

    def describe(self, i):
        return f"{_clock(i * self.STEP)} / {_clock(self.length)}"


def _clock(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:04.1f}"


def _preview(img):
    img = img.copy()
    img.thumbnail(PREVIEW_MAX, Image.LANCZOS)
    if img.mode == "RGBA":
        # checkerboard behind transparent areas
        board = Image.new("RGB", img.size, (204, 204, 204))
        tile = Image.new("RGB", (8, 8), (255, 255, 255))
        for y in range(0, img.size[1], 8):
            for x in range((y // 8) % 2 * 8, img.size[0], 16):
                board.paste(tile, (x, y))
        board.paste(img, mask=img.getchannel("A"))
        img = board
    return img


def pick_frame(path, target_label):
    """Let the user choose one picture from an animation or video. Returns it, or None."""
    import tkinter as tk
    from tkinter import ttk

    from PIL import ImageTk

    source = VideoFrames(path) if not _is_image(path) else AnimationFrames(path)

    root = _new_root(f"{APP_NAME} – " + tr("Pick a frame", "Bild auswählen"))
    frame = ttk.Frame(root, padding=16)
    frame.pack()
    ttk.Label(frame, text=os.path.basename(path), font=_bold(root)).pack(anchor="w")
    ttk.Label(frame, text=tr(f"Choose the picture to save as {target_label}.",
                             f"Wähle das Bild, das als {target_label} gespeichert wird."),
              foreground="gray").pack(anchor="w", pady=(2, 10))

    canvas = tk.Label(frame, background="#202020", width=PREVIEW_MAX[0], height=PREVIEW_MAX[1])
    canvas.pack()

    controls = ttk.Frame(frame)
    controls.pack(fill="x", pady=(10, 0))
    position = tk.IntVar(value=0)
    caption = ttk.Label(controls, width=22)

    state = {"shown": None, "pending": None, "photo": None, "result": None}

    def show(i):
        i = max(0, min(source.count - 1, i))
        if state["shown"] == i:
            return
        try:
            img = source.frame(i)
        except Exception as e:
            caption.configure(text=tr(f"Error: {e}", f"Fehler: {e}"))
            return
        state["photo"] = ImageTk.PhotoImage(_preview(img))
        canvas.configure(image=state["photo"], width=PREVIEW_MAX[0], height=PREVIEW_MAX[1])
        caption.configure(text=source.describe(i))
        state["shown"] = i

    def on_slide(_value):
        position.set(round(float(scale.get())))
        # videos need ffmpeg per frame, so wait until the slider rests a moment
        if state["pending"]:
            root.after_cancel(state["pending"])
        delay = 150 if isinstance(source, VideoFrames) else 0
        state["pending"] = root.after(delay, lambda: show(position.get()))

    def step(delta):
        i = max(0, min(source.count - 1, position.get() + delta))
        position.set(i)
        scale.set(i)
        show(i)

    ttk.Button(controls, text="◀", width=3, command=lambda: step(-1)).pack(side="left")
    scale = ttk.Scale(controls, from_=0, to=max(source.count - 1, 0), orient="horizontal",
                      length=420, command=on_slide)
    scale.pack(side="left", padx=6, fill="x", expand=True)
    ttk.Button(controls, text="▶", width=3, command=lambda: step(1)).pack(side="left")
    caption.pack(side="left", padx=(10, 0))

    def save():
        try:
            state["result"] = source.frame(position.get())
        except Exception as e:
            message(tr(f"Couldn't read the picture:\n\n{e}",
                       f"Bild konnte nicht gelesen werden:\n\n{e}"), error=True)
            return
        root.destroy()

    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=(14, 0))
    ttk.Button(buttons, text=tr("Cancel", "Abbrechen"), command=root.destroy).pack(side="right")
    ttk.Button(buttons, text=tr(f"Save as {target_label}", f"Als {target_label} speichern"),
               command=save).pack(side="right", padx=(0, 8))

    root.bind("<Left>", lambda e: step(-1))
    root.bind("<Right>", lambda e: step(1))
    root.bind("<Return>", lambda e: save())
    root.bind("<Escape>", lambda e: root.destroy())

    show(0)
    _center(root)
    root.mainloop()
    return state["result"]


def _is_image(path):
    return group_of(path) == "image"


# --- format picker ---------------------------------------------------------------

def shared_targets(files):
    """Targets every selected file can be converted to, in menu order."""
    lists = [[t for t in targets_for(os.path.splitext(f)[1].lower()) if t is not SEP]
             for f in files]
    return [t for t in lists[0] if all(t in other for other in lists)]


def pick_target(files):
    """Format window for "Open with" and the scripts menu. Returns a target, or None."""
    from tkinter import ttk

    targets = shared_targets(files)
    if not targets:
        return None
    root = _new_root(APP_NAME)
    frame = ttk.Frame(root, padding=16)
    frame.pack()
    header = os.path.basename(files[0]) if len(files) == 1 else tr(f"{len(files)} files",
                                                                   f"{len(files)} Dateien")
    ttk.Label(frame, text=header, font=_bold(root)).grid(row=0, column=0, columnspan=4, sticky="w")
    ttk.Label(frame, text=tr("Convert to:", "Umwandeln in:"), foreground="gray").grid(
        row=1, column=0, columnspan=4, sticky="w", pady=(2, 10))
    chosen = {}

    def choose(target):
        chosen["target"] = target
        root.destroy()

    group = group_of(files[0])
    for i, target in enumerate(targets):
        # a still image from a video is different from converting it: keep that visible
        text = LABELS[target]
        if group == "video" and target in ("png", "jpg"):
            text = menu_label(group, target)
        ttk.Button(frame, text=text, command=lambda t=target: choose(t)).grid(
            row=2 + i // 4, column=i % 4, padx=3, pady=3, sticky="ew")
    root.bind("<Escape>", lambda e: root.destroy())
    _center(root)
    root.mainloop()
    return chosen.get("target")
