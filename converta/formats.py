"""Which file types Converta knows and what each one can be turned into."""
import os

from .i18n import tr

SEP = None  # separator line in the context menu

LABELS = {
    # images
    "png": "PNG", "jpg": "JPG", "webp": "WEBP", "avif": "AVIF", "bmp": "BMP",
    "gif": "GIF", "tiff": "TIFF", "ico": "ICO",
    # audio
    "mp3": "MP3", "wav": "WAV", "flac": "FLAC", "ogg": "OGG", "m4a": "M4A",
    "opus": "OPUS", "aac": "AAC", "wma": "WMA",
    # video
    "mp4": "MP4", "mkv": "MKV", "webm": "WEBM", "mov": "MOV", "avi": "AVI",
    # documents
    "pdf": "PDF", "docx": "Word (DOCX)", "odt": "ODT", "rtf": "RTF", "txt": "Text (TXT)",
    "xlsx": "Excel (XLSX)", "ods": "ODS", "csv": "CSV",
    "pptx": "PowerPoint (PPTX)", "odp": "ODP",
    # 3D / CAD
    "stl": "STL", "obj": "OBJ", "3mf": "3MF", "ply": "PLY", "glb": "GLB", "off": "OFF",
    "svg": "SVG",
}

IMAGE_TARGETS = ["png", "jpg", "webp", "avif", "bmp", "gif", "tiff", "ico", SEP, "pdf"]
AUDIO_TARGETS = ["mp3", "wav", "flac", "ogg", "m4a", "opus", "aac", "wma"]
VIDEO_TARGETS = ["mp4", "mkv", "webm", "mov", "avi", "gif",
                 SEP, "mp3", "wav", "flac", "m4a", "ogg",
                 SEP, "png", "jpg"]

# group -> (source extensions, targets in menu order)
GROUPS = {
    "image": ([".png", ".jpg", ".jpeg", ".jfif", ".webp", ".avif", ".bmp", ".gif",
               ".tif", ".tiff", ".ico"], IMAGE_TARGETS),
    "audio": ([".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma",
               ".aif", ".aiff"], AUDIO_TARGETS),
    "video": ([".mp4", ".mkv", ".webm", ".mov", ".avi", ".wmv", ".flv", ".m4v",
               ".mpg", ".mpeg", ".3gp"], VIDEO_TARGETS),
    "pdf": ([".pdf"], ["docx", "txt", SEP, "png", "jpg"]),
    "word": ([".docx", ".doc", ".odt", ".rtf"], ["pdf", SEP, "docx", "odt", "rtf", "txt"]),
    "sheet": ([".xlsx", ".xls", ".ods"], ["pdf", SEP, "xlsx", "ods", "csv"]),
    "slides": ([".pptx", ".ppt", ".odp"], ["pdf", SEP, "pptx", "odp"]),
    "model": ([".stl", ".obj", ".3mf", ".ply", ".off", ".glb", ".gltf"],
              ["stl", "obj", "3mf", "ply", "glb", "off"]),
    "cad": ([".step", ".stp", ".iges", ".igs"], ["stl", "3mf", "obj", "ply", "glb"]),
    "dxf": ([".dxf"], ["pdf", "svg", "png"]),
}

# extra menu entries for single extensions
EXTRA_TARGETS = {".gif": [SEP, "mp4", "webm"]}

# extensions whose own format key differs from the extension itself
OWN_KEY = {".jpeg": "jpg", ".jfif": "jpg", ".tif": "tiff"}

# image targets that hold exactly one picture (animations need a frame chosen)
SINGLE_FRAME_IMAGES = {"png", "jpg", "bmp", "tiff", "ico", "pdf"}
VIDEO_KEYS = {"mp4", "mkv", "webm", "mov", "avi"}


def ext_of(path):
    return os.path.splitext(path)[1].lower()


def group_of(path):
    ext = ext_of(path)
    for group, (exts, _) in GROUPS.items():
        if ext in exts:
            return group
    return None


def own_key(ext):
    return OWN_KEY.get(ext, ext[1:])


def targets_for(ext):
    """Menu targets for a source extension, own format left out, no doubled separators."""
    group = next(g for g, (exts, _) in GROUPS.items() if ext in exts)
    items = [t for t in GROUPS[group][1] + EXTRA_TARGETS.get(ext, []) if t != own_key(ext)]
    cleaned = []
    for t in items:
        if t is SEP and (not cleaned or cleaned[-1] is SEP):
            continue
        cleaned.append(t)
    while cleaned and cleaned[-1] is SEP:
        cleaned.pop()
    return cleaned


def all_source_exts():
    return [ext for exts, _ in GROUPS.values() for ext in exts]


def menu_label(group, target):
    label = LABELS[target]
    if group == "pdf" and target in ("png", "jpg"):
        return tr(f"Pages as {label}", f"Seiten als {label}")
    if group == "video" and target in ("png", "jpg"):
        return tr(f"Still image as {label}…", f"Einzelbild als {label}…")
    if group == "video" and target in AUDIO_TARGETS:
        return tr(f"Audio as {label}", f"Audio als {label}")
    return tr(f"Convert to {label}", f"In {label} umwandeln")
