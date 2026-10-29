<p align="center">
  <img src="assets/converta.png" width="128" alt="Converta logo">
</p>

<h1 align="center">Converta</h1>

<p align="center">
  Convert files straight from the Windows Explorer right-click menu.<br>
  Images, audio, video, PDF, Office documents, 3D models and CAD — no upload, everything stays on your PC.
</p>

<p align="center">
  <a href="https://converta.erenk.de"><b>Website</b></a> ·
  <a href="https://github.com/Erennkrb/Converta/releases/latest"><b>Download</b></a>
</p>

---

## How it works

Right-click a file → **Converta** → pick a format. The converted file appears next to the original; nothing is ever overwritten.

On Windows 11 the entry sits in the classic menu: **Show more options**, or **Shift + right-click**.

## Supported formats

| Source | Converts to |
|---|---|
| **Images** png, jpg/jpeg/jfif, webp, avif, bmp, gif, tif/tiff, ico | PNG, JPG, WEBP, AVIF, BMP, GIF, TIFF, ICO, PDF · GIF also to MP4, WEBM |
| **Audio** mp3, wav, flac, ogg, m4a, aac, opus, wma, aif/aiff | MP3, WAV, FLAC, OGG, M4A, OPUS, AAC, WMA |
| **Video** mp4, mkv, webm, mov, avi, wmv, flv, m4v, mpg/mpeg, 3gp | MP4, MKV, WEBM, MOV, AVI, GIF · audio track as MP3, WAV, FLAC, M4A, OGG · single frame as PNG/JPG |
| **PDF** | Word (DOCX), TXT, pages as PNG/JPG |
| **Word** docx, doc, odt, rtf | PDF, DOCX, ODT, RTF, TXT |
| **Excel** xlsx, xls, ods | PDF, XLSX, ODS, CSV |
| **PowerPoint** pptx, ppt, odp | PDF, PPTX, ODP |
| **3D models** stl, obj, 3mf, ply, off, glb, gltf | STL, OBJ, 3MF, PLY, GLB, OFF |
| **CAD** step/stp, iges/igs | STL, 3MF, OBJ, PLY, GLB (meshed in millimetres, ready for slicers) |
| **DXF drawings** | PDF, SVG, PNG |

- Transparency is kept where the target format supports it (JPG/BMP/PDF get a white background).
- Animated GIF/WEBP/AVIF stay animated when converted to GIF, WEBP or AVIF. For single-picture formats a window lets you pick the exact frame — the same for taking a still from a video.
- Selecting several files converts them all in one go.

## Requirements

- Windows 10 or 11, 64-bit
- **Audio & video:** [FFmpeg](https://ffmpeg.org) is downloaded automatically on the first audio/video conversion (pinned build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), verified by SHA-256).
- **Word, Excel, PowerPoint:** Microsoft Office or the free [LibreOffice](https://www.libreoffice.org/download/).

## Building from source

```powershell
winget install Python.Python.3.13 JRSoftware.InnoSetup
python -m pip install -r requirements.txt

# run from source (registers the context menu, asks for admin rights)
python main.py --install

# build the installer -> dist\Converta-Setup-<version>.exe
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

| Path | What's inside |
|---|---|
| `converta/formats.py` | every supported type and its menu entries |
| `converta/images.py` · `media.py` · `documents.py` · `models.py` | conversions (Pillow · FFmpeg · PyMuPDF/pdf2docx/Office · trimesh/OpenCASCADE/ezdxf) |
| `converta/ui.py` | progress window and frame picker |
| `converta/shell.py` | Explorer context-menu registration |
| `installer/converta.iss` | Inno Setup wizard |
| `website/` | converta.erenk.de (Cloudflare) |

## License

[AGPL-3.0](LICENSE). Converta uses [PyMuPDF](https://github.com/pymupdf/PyMuPDF), which is AGPL-licensed.
