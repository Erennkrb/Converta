"""3D models (trimesh), CAD solids (OpenCASCADE via cascadio) and DXF drawings (ezdxf)."""
import io
import os

from .i18n import tr
from .paths import output_path

CAD_TYPES = {".step": "step", ".stp": "step", ".iges": "iges", ".igs": "iges"}

# meshing accuracy for CAD solids: 0.01 mm chord error, ~11 degrees per facet
CAD_TOL_LINEAR = 0.01
CAD_TOL_ANGULAR = 0.2


def _load(src):
    import trimesh

    ext = os.path.splitext(src)[1].lower()
    if ext in CAD_TYPES:
        import cascadio

        with open(src, "rb") as f:
            glb = cascadio.load(f.read(), file_type=CAD_TYPES[ext],
                                tol_linear=CAD_TOL_LINEAR, tol_angular=CAD_TOL_ANGULAR)
        scene = trimesh.load(io.BytesIO(glb), file_type="glb", force="scene")
        # glTF is always in metres; CAD files and slicers expect millimetres
        scene.apply_scale(1000)
        return scene
    return trimesh.load(src, force="scene")


def _single_mesh(scene):
    import trimesh

    if hasattr(scene, "to_mesh"):
        return scene.to_mesh()
    return trimesh.util.concatenate(scene.dump())


def convert(src, target, progress=None):
    scene = _load(src)
    if not scene.geometry:
        raise RuntimeError(tr("This file doesn't contain a 3D model.",
                              "Die Datei enthält kein 3D-Modell."))
    dst = output_path(src, target)
    if target in ("glb", "3mf", "obj"):
        # these keep separate parts and colours
        scene.export(dst, file_type=target)
    else:
        _single_mesh(scene).export(dst, file_type=target)
    return dst


def dxf_convert(src, target, progress=None):
    import ezdxf
    from ezdxf import recover
    from ezdxf.addons.drawing import Frontend, RenderContext, layout

    try:
        doc = ezdxf.readfile(src)
    except ezdxf.DXFStructureError:
        doc, _ = recover.readfile(src)  # damaged files from other programs
    msp = doc.modelspace()
    page = layout.Page(0, 0, layout.Units.mm, margins=layout.Margins.all(10))  # 0 = fit drawing
    dst = output_path(src, target)

    if target == "svg":
        from ezdxf.addons.drawing import svg

        backend = svg.SVGBackend()
        Frontend(RenderContext(doc), backend).draw_layout(msp)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(backend.get_string(page))
        return dst

    from ezdxf.addons.drawing import pymupdf as mupdf_backend

    backend = mupdf_backend.PyMuPdfBackend()
    Frontend(RenderContext(doc), backend).draw_layout(msp)
    if target == "pdf":
        data = backend.get_pdf_bytes(page)
    else:
        data = backend.get_pixmap_bytes(page, fmt=target, dpi=200)
    with open(dst, "wb") as f:
        f.write(data)
    return dst
