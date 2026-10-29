"""Small Tk windows: progress for slow conversions and the frame picker."""
import ctypes
import os
import threading

from PIL import Image

from . import APP_NAME
from .paths import asset

PREVIEW_MAX = (640, 400)


def message(text, error=False):
    flags = 0x10 if error else 0x40  # MB_ICONERROR / MB_ICONINFORMATION
    ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, flags | 0x10000)  # MB_SETFOREGROUND


def _new_root(title):
    import tkinter as tk

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    root.title(title)
    root.resizable(False, False)
    try:
        root.iconbitmap(asset("converta.ico"))
    except Exception:
        pass
    return root


def _center(root):
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    root.lift()
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
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

    if not show_window:
        for path, fn in jobs:
            run_one(path, fn, lambda fraction, text=None: None)
        return errors

    from tkinter import ttk

    root = _new_root(APP_NAME)
    frame = ttk.Frame(root, padding=16)
    frame.pack()
    title = ttk.Label(frame, font=("Segoe UI", 10, "bold"), width=48)
    title.pack(anchor="w")
    name = ttk.Label(frame, foreground="gray", width=48)
    name.pack(anchor="w", pady=(2, 10))
    bar = ttk.Progressbar(frame, length=380, maximum=1000)
    bar.pack()
    state = {"index": 0, "fraction": None, "text": None, "done": False, "cancel": False}

    def cancel():
        state["cancel"] = True
        cancel_button.state(["disabled"])
        title.configure(text="Wird abgebrochen…")

    cancel_button = ttk.Button(frame, text="Abbrechen", command=cancel)
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
                title.configure(text="Wird umgewandelt…" if len(jobs) == 1
                                else f"Datei {i + 1} von {len(jobs)} wird umgewandelt…")
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
        return f"Frame {i + 1} von {self.count}"


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

    root = _new_root(f"{APP_NAME} – Bild auswählen")
    frame = ttk.Frame(root, padding=16)
    frame.pack()
    ttk.Label(frame, text=os.path.basename(path), font=("Segoe UI", 10, "bold")).pack(anchor="w")
    ttk.Label(frame, text=f"Wähle das Bild, das als {target_label} gespeichert wird.",
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
            caption.configure(text=f"Fehler: {e}")
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
            message(f"Bild konnte nicht gelesen werden:\n\n{e}", error=True)
            return
        root.destroy()

    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=(14, 0))
    ttk.Button(buttons, text="Abbrechen", command=root.destroy).pack(side="right")
    ttk.Button(buttons, text=f"Als {target_label} speichern", command=save).pack(
        side="right", padx=(0, 8))

    root.bind("<Left>", lambda e: step(-1))
    root.bind("<Right>", lambda e: step(1))
    root.bind("<Return>", lambda e: save())
    root.bind("<Escape>", lambda e: root.destroy())

    show(0)
    _center(root)
    root.mainloop()
    return state["result"]


def _is_image(path):
    from .formats import group_of

    return group_of(path) == "image"
