"""Document conversions: PDF via PyMuPDF/pdf2docx, Office formats via Word or LibreOffice."""
import glob
import os
import shutil
import subprocess
import tempfile
import winreg

from .paths import data_dir, output_path

CREATE_NO_WINDOW = 0x08000000

# Word's SaveAs2 FileFormat values
WORD_FORMATS = {"pdf": 17, "docx": 16, "rtf": 6, "txt": 7, "odt": 23}

# LibreOffice --convert-to filters where the plain extension isn't enough
LIBREOFFICE_FILTERS = {
    "txt": "txt:Text (encoded):UTF8",
    "csv": "csv:Text - txt - csv (StarCalc):44,34,76",
}


class ToolMissing(Exception):
    pass


# --- PDF ---------------------------------------------------------------------

def from_pdf(src, target, progress=None):
    if target == "docx":
        return pdf_to_docx(src)
    if target == "txt":
        return pdf_to_txt(src)
    return pdf_to_images(src, target, progress)


def pdf_to_docx(src):
    from pdf2docx import Converter

    dst = output_path(src, "docx")
    converter = Converter(src)
    try:
        converter.convert(dst)
    finally:
        converter.close()
    return dst


def pdf_to_txt(src):
    import pymupdf

    dst = output_path(src, "txt")
    with pymupdf.open(src) as doc, open(dst, "w", encoding="utf-8") as out:
        for page in doc:
            out.write(page.get_text())
            out.write("\f")  # page break
    return dst


def pdf_to_images(src, target, progress=None):
    """Every page as its own picture: 'name - Seite 1.png', ... (just 'name.png' for one page)."""
    import pymupdf

    with pymupdf.open(src) as doc:
        count = doc.page_count
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=200)
            suffix = f" - Seite {i + 1}" if count > 1 else ""
            dst = output_path(src, target, suffix)
            if target == "jpg":
                pix.save(dst, jpg_quality=92)
            else:
                pix.save(dst)
            if progress:
                progress((i + 1) / count)
    return dst


# --- Office formats ------------------------------------------------------------

def word_installed():
    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID").Close()
        return True
    except OSError:
        return False


def find_libreoffice():
    found = shutil.which("soffice.com") or shutil.which("soffice.exe")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        hits = glob.glob(os.path.join(base, "LibreOffice*", "program", "soffice.com"))
        if hits:
            return hits[0]
    return None


def office_convert(src, target, progress=None):
    ext = os.path.splitext(src)[1].lower()
    word_file = ext in (".docx", ".doc", ".odt", ".rtf")
    if word_file and target in WORD_FORMATS and word_installed():
        return _convert_with_word(src, target)
    soffice = find_libreoffice()
    if soffice:
        return _convert_with_libreoffice(soffice, src, target)
    raise ToolMissing("Dafür wird Microsoft Office oder LibreOffice benötigt "
                      "(kostenlos: libreoffice.org).")


def _convert_with_word(src, target):
    import pythoncom
    import win32com.client

    dst = output_path(src, target)
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    try:
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(os.path.abspath(src), ReadOnly=True,
                                  AddToRecentFiles=False, ConfirmConversions=False)
        try:
            doc.SaveAs2(dst, FileFormat=WORD_FORMATS[target])
        finally:
            doc.Close(False)
    finally:
        word.Quit()
        pythoncom.CoUninitialize()
    return dst


def _convert_with_libreoffice(soffice, src, target):
    dst = output_path(src, target)
    # own profile, so a LibreOffice window the user has open doesn't block us
    profile = "file:///" + os.path.join(data_dir(), "lo-profile").replace("\\", "/")
    with tempfile.TemporaryDirectory() as outdir:
        result = subprocess.run(
            [soffice, f"-env:UserInstallation={profile}", "--headless", "--norestore",
             "--convert-to", LIBREOFFICE_FILTERS.get(target, target), "--outdir", outdir, src],
            capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=600)
        produced = glob.glob(os.path.join(outdir, "*"))
        if not produced:
            detail = result.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(detail or "LibreOffice konnte die Datei nicht umwandeln.")
        shutil.move(produced[0], dst)
    return dst
