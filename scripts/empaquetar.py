#!/usr/bin/env python3
"""Crea una entrega portable y un inventario SHA-256 sin archivos de entorno."""
import zipfile
from pathlib import Path
from entorno import ROOT, sha256


def main():
    archive=ROOT/"Entrega_Reto_Ambulancias.zip"
    manifest=ROOT/"MANIFEST.sha256"
    excluded={".git",".agents",".aws",".codex",".venv","__pycache__",".mplconfig","historial","diagnostico","smoke","publicacion"}
    files=sorted(p for p in ROOT.rglob("*") if p.is_file()
        and not (set(p.relative_to(ROOT).parts)&excluded)
        and p not in [archive,manifest] and p.suffix!=".pyc"
        and p.name!="core" and not p.name.startswith("core."))
    manifest.write_text("".join(f"{sha256(p)}  {p.relative_to(ROOT)}\n" for p in files))
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for p in files+[manifest]:
            out.write(p,Path("RetoAmbulancia")/p.relative_to(ROOT))
    with zipfile.ZipFile(archive) as out:
        bad=out.testzip()
        if bad:
            raise RuntimeError(f"ZIP corrupto: {bad}")
    print(f"{archive.name}: {archive.stat().st_size/1024**2:.1f} MiB; {len(files)+1} archivos; CRC verificado")


if __name__=="__main__":
    main()
