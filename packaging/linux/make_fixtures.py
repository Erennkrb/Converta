"""Small sample files for the Linux smoke tests. Usage: make_fixtures.py OUT_DIR"""
import os
import sys
import urllib.request

import docx
import ezdxf
import pymupdf
import trimesh
from PIL import Image

out = sys.argv[1]
os.makedirs(out, exist_ok=True)


def path(name):
    return os.path.join(out, name)


Image.new("RGBA", (64, 48), (40, 120, 255, 160)).save(path("sample.png"))
frames = [Image.new("RGB", (32, 32), c) for c in ("red", "green", "blue")]
frames[0].save(path("anim.gif"), save_all=True, append_images=frames[1:], duration=100, loop=0)
trimesh.creation.box((20, 10, 5)).export(path("box.stl"))

doc = pymupdf.open()
doc.new_page().insert_text((72, 72), "Converta test")
doc.save(path("sample.pdf"))

word = docx.Document()
word.add_paragraph("Converta test")
word.save(path("sample.docx"))

drawing = ezdxf.new()
drawing.modelspace().add_circle((0, 0), 10)
drawing.saveas(path("plan.dxf"))

urllib.request.urlretrieve(
    "https://raw.githubusercontent.com/mikedh/trimesh/main/models/featuretype.STEP", path("part.step"))
