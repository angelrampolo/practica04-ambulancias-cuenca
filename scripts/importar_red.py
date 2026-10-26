#!/usr/bin/env python3
"""Incorpora el ZIP docente y registra sus huellas sin extraer rutas arbitrarias."""
import argparse
import datetime
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from entorno import ROOT, guardar_json, sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip",type=Path,nargs="?",default=ROOT/"datos/docente/cuenca_net.zip")
    args=parser.parse_args()
    with zipfile.ZipFile(args.zip) as archive:
        members=[m for m in archive.infolist() if not m.is_dir()]
        if len(members)!=1 or Path(members[0].filename).name!="cuenca_net.xml":
            parser.error("Se espera un ZIP que contenga únicamente cuenca_net.xml")
        raw=archive.read(members[0])  # zipfile comprueba el CRC al leer.
    if ET.fromstring(raw).tag!="net":
        parser.error("El XML no es una red SUMO")
    destination=ROOT/"datos/docente/cuenca_net.zip"
    destination.parent.mkdir(parents=True,exist_ok=True)
    if args.zip.resolve()!=destination.resolve():
        shutil.copy2(args.zip,destination)
    net=ROOT/"datos/cuenca_net.xml"
    net.write_bytes(raw)
    provenance=ROOT/"datos/procedencia_red.json"
    previous=json.loads(provenance.read_text()) if provenance.exists() else {}
    digest=sha256(net)
    timestamp=previous.get("incorporado_utc") if previous.get("red_sha256")==digest else None
    guardar_json(provenance,dict(tipo="red_docente_aportada_por_usuario",
        archivo_zip="datos/docente/cuenca_net.zip",nombre_original="cuenca_net.xml",
        zip_sha256=sha256(destination),red_sha256=digest,
        incorporado_utc=timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat(),
        hospitales="Se mantienen coordenadas OSM porque el ZIP contiene únicamente la red.",
        respaldo_anterior="historial/Entrega_OSM_20261021.zip (respaldo local, excluido de la entrega)"))
    print(f"Red incorporada: {net}; SHA-256: {digest}")


if __name__=="__main__":
    main()
