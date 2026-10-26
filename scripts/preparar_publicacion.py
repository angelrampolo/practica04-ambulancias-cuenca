#!/usr/bin/env python3
"""Prepara código para GitHub y fuentes LaTeX sin publicar ni modificar remotos."""
import json
import shutil
import zipfile
from pathlib import Path
from entorno import ROOT, guardar_json, sha256


def zip_files(target,files,prefix="RetoAmbulancia"):
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for source,relative in files:
            archive.write(source,Path(prefix)/relative)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None,"CRC incorrecto"


def main():
    out=ROOT/"publicacion";repo=out/"github"
    repo.mkdir(parents=True,exist_ok=True)
    selected=[]
    for base in ["scripts","pruebas","docs","datos","escenario","salida"]:
        for p in sorted((ROOT/base).rglob("*")):
            if not p.is_file():continue
            rel=p.relative_to(ROOT)
            if set(rel.parts)&{"__pycache__","build","diagnostico"}:continue
            if rel.as_posix() in {"datos/cuenca_net.xml","datos/cuenca_osm.xml"}:continue
            if base=="escenario" and p.name not in {"reto.sumocfg","vtypes.add.xml","macro.add.xml"}:continue
            if base=="salida" and p.suffix==".xml" and p.name not in {"colisiones.xml","estadisticas.xml"}:continue
            if p.suffix in {".pyc",".log"}:continue
            selected.append(p)
    selected.extend(ROOT/name for name in ["README.md","Makefile","requirements.txt",".gitignore"])
    for p in selected:
        dest=repo/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    note=("# Código de la Práctica 04\n\n"
        "Este paquete conserva código, ZIP docente, coordenadas, informe y resultados ligeros. "
        "La red XML extraída, el OSM de coordenadas y los XML voluminosos de tráfico están en la entrega completa. "
        "Para recrear las entradas y ejecutar la auditoría en este repositorio:\n\n"
        "```bash\npython3 scripts/importar_red.py datos/docente/cuenca_net.zip\nmake reproducir\n```\n\n"
        "Consulta los requisitos de Docker, Python y Tectonic más abajo.\n\n")
    (repo/"README.md").write_text(note+(ROOT/"README.md").read_text())
    with (repo/".gitignore").open("a") as f:
        f.write("\n# Entradas extraíbles, productos de ejecución y paquetes locales\n"
            "datos/cuenca_net.xml\ndatos/cuenca_osm.xml\nescenario/cuenca_ciudad.net.xml\n"
            "escenario/fondo_*\nsalida/base/macro.xml\nsalida/**/tripinfo.xml\nsalida/**/summary.xml\n"
            "docs/latex/build/\nhistorial/\npublicacion/\nEntrega_Reto_Ambulancias.zip\nCodigo_GitHub.zip\nInforme_LaTeX.zip\n")
    files=[(p,p.relative_to(repo)) for p in repo.rglob("*") if p.is_file() and ".git" not in p.relative_to(repo).parts]
    zip_files(ROOT/"Codigo_GitHub.zip",files)
    texfiles=[(p,Path(p.name)) for p in (ROOT/"docs/latex").glob("*") if p.is_file() and p.suffix in {".tex",".cls",".md"}]
    texfiles.extend((p,Path("figuras")/p.name) for p in (ROOT/"salida/figuras").glob("*.pdf"))
    texfiles.extend((p,Path("capturas")/p.name) for p in (ROOT/"salida/visual").glob("*.png"))
    zip_files(ROOT/"Informe_LaTeX.zip",texfiles,prefix="Informe_IEEE")
    shutil.copy2(ROOT/"docs/Informe_Reto_Ambulancias.pdf",out/"Practica04_AngelApolo_IEEE.pdf")
    receipt=out/"github_verificado.json"
    publication=json.loads(receipt.read_text()) if receipt.exists() else {}
    guardar_json(out/"preparacion.json",dict(publicado_github=publication.get("codigo_publicado",False),
        github_url=publication.get("url"),github_commit_verificado=publication.get("commit"),
        cargado_plataforma=False,
        documentos=[dict(archivo=str(p.relative_to(ROOT)),sha256=sha256(p)) for p in
            [ROOT/"Codigo_GitHub.zip",ROOT/"Informe_LaTeX.zip",out/"Practica04_AngelApolo_IEEE.pdf"]]))
    for p in [ROOT/"Codigo_GitHub.zip",ROOT/"Informe_LaTeX.zip"]:
        print(f"{p.name}: {p.stat().st_size/1024**2:.2f} MiB; CRC verificado")
    print("Carpeta preparada: publicacion/github. No se realizó ninguna publicación remota.")


if __name__=="__main__":main()
