# Builds dist\Converta-Setup-<version>.exe
#   1. Converta.exe (PyInstaller, onedir: starts fast from the context menu)
#   2. trim files nothing uses
#   3. setup wizard (Inno Setup)
# ffmpeg is not bundled: Converta downloads it on the first audio/video conversion.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = @($env:PYTHON, "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe") |
    Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $python) { $python = "python" }
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
          "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup (ISCC.exe) not found" }

$version = (Select-String -Path converta\__init__.py -Pattern '__version__ = "(.+)"').Matches[0].Groups[1].Value
Write-Host "Building Converta $version"

# 1. exe
# pymupdf.layout/onnxruntime: optional AI layout analysis (~75 MB), Converta doesn't use it
& $python -m PyInstaller --noconfirm --clean --windowed --onedir --name Converta `
    --icon "$PSScriptRoot\assets\converta.ico" --add-data "$PSScriptRoot\assets;assets" `
    --hidden-import pythoncom --hidden-import win32com.client `
    --collect-data pdf2docx --collect-data trimesh --collect-data ezdxf `
    --collect-binaries cascadio --hidden-import networkx `
    --exclude-module pymupdf.layout --exclude-module onnxruntime `
    --exclude-module matplotlib --exclude-module scipy --exclude-module pandas `
    --distpath build\pyinstaller --workpath build\work --specpath build `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# 2. OpenCV's video I/O plugin (~29 MB): pdf2docx only uses OpenCV on images
Remove-Item build\pyinstaller\Converta\_internal\cv2\opencv_videoio_ffmpeg*.dll -ErrorAction SilentlyContinue

# 3. setup
& $iscc "/DAppVersion=$version" installer\converta.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
Get-Item "dist\Converta-Setup-$version.exe"
