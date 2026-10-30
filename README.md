<p align="center">
  <img src="assets/converta.png" width="128" alt="Converta logo">
</p>

<h1 align="center">Converta</h1>

<p align="center">
  Convert files straight from your Windows right-click menu, without any uploads.<br>
  Images, audio, video, PDFs, Office docs, 3D models, and CAD — everything stays entirely on your PC.
</p>

<p align="center">
  <a href="https://converta.erenk.de"><b>Website</b></a> ·
  <a href="https://github.com/Erennkrb/Converta/releases/latest"><b>Download</b></a>
</p>

---

## How it works

Just right-click any file, hover over **Converta**, and pick your format. The newly converted file pops up right next to your original one. Don't worry—nothing ever gets overwritten.

*(On Windows 11, you'll find the option under **Show more options**, or by hitting `Shift + right-click`.)*

## Supported formats

| Source | Converts to |
|---|---|
| **Images** `png`, `jpg`/`jpeg`/`jfif`, `webp`, `avif`, `bmp`, `gif`, `tif`/`tiff`, `ico` | PNG, JPG, WEBP, AVIF, BMP, GIF, TIFF, ICO, PDF <br>*(GIFs can also become MP4 or WEBM)* |
| **Audio** `mp3`, `wav`, `flac`, `ogg`, `m4a`, `aac`, `opus`, `wma`, `aif`/`aiff` | MP3, WAV, FLAC, OGG, M4A, OPUS, AAC, WMA |
| **Video** `mp4`, `mkv`, `webm`, `mov`, `avi`, `wmv`, `flv`, `m4v`, `mpg`/`mpeg`, `3gp` | MP4, MKV, WEBM, MOV, AVI, GIF <br>· Extract audio tracks (MP3, WAV, FLAC, M4A, OGG) <br>· Grab a single frame (PNG, JPG) |
| **PDF** | Word (`DOCX`), `TXT`, or pages as PNG/JPG |
| **Word** `docx`, `doc`, `odt`, `rtf` | PDF, DOCX, ODT, RTF, TXT |
| **Excel** `xlsx`, `xls`, `ods` | PDF, XLSX, ODS, CSV |
| **PowerPoint** `pptx`, `ppt`, `odp` | PDF, PPTX, ODP |
| **3D models** `stl`, `obj`, `3mf`, `ply`, `off`, `glb`, `gltf` | STL, OBJ, 3MF, PLY, GLB, OFF |
| **CAD** `step`/`stp`, `iges`/`igs` | STL, 3MF, OBJ, PLY, GLB <br>*(automatically meshed in millimetres, ready for slicers)* |
| **DXF drawings** | PDF, SVG, PNG |

- **Transparency:** Preserved wherever the target format supports it (formats like JPG, BMP, and PDF will automatically get a clean white background instead).
- **Animations & Frames:** Animated files (GIF, WEBP, AVIF) stay animated when converted to another animation format. For single-picture formats or videos, a quick window pops up letting you pick the exact frame you want.
- **Batch processing:** Highlight and select multiple files to convert them all in one go.

## What you'll need

- Windows 10 or 11 (64-bit)
- **Audio & video conversions:** [FFmpeg](https://ffmpeg.org). Don't sweat installing it manually—Converta will grab a clean, verified build automatically the first time you need it.
- **Office documents:** Either Microsoft Office or the free [LibreOffice](https://www.libreoffice.org/download/) installed on your system.

## Building from source

If you want to tinker or build it yourself:

```powershell
winget install Python.Python.3.13 JRSoftware.InnoSetup
python -m pip install -r requirements.txt

# run from source (this registers the context menu and will ask for admin rights)
python main.py --install

# build the installer -> dist\Converta-Setup-<version>.exe
powershell -ExecutionPolicy Bypass -File .\build.ps1
