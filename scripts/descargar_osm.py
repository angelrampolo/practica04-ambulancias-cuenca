#!/usr/bin/env python3
"""Alternativa documentada cuando falta cuenca_net.xml del docente.

Descarga datos públicos de OpenStreetMap. No equivale a la red docente.
El XML se conserva para poder repetir sin depender de cambios del mapa.
"""
import argparse
import datetime
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from entorno import ROOT, guardar_json, sha256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--endpoint",default="https://overpass-api.de/api/interpreter")
    args=p.parse_args()
    query='''[out:xml][timeout:180];
    (way["highway"](-2.97,-79.07,-2.83,-78.92);
     nwr["amenity"="hospital"](-2.97,-79.07,-2.83,-78.92););
    (._;>;);out body;'''
    req=urllib.request.Request(args.endpoint,data=urllib.parse.urlencode({"data":query}).encode(),
                               headers={"User-Agent":"RetoAmbulancia-academic/1.0"})
    with urllib.request.urlopen(req,timeout=240) as response:
        data=response.read()
    root=ET.fromstring(data)
    if root.find("remark") is not None:
        raise RuntimeError(root.findtext("remark"))
    path=ROOT/"datos/cuenca_osm.xml"
    path.write_bytes(data)
    guardar_json(ROOT/"datos/procedencia_osm.json",dict(url=args.endpoint,query=query,
        retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sha256=sha256(path),bytes=len(data),licencia="Open Database License (ODbL)",
        attribution="© OpenStreetMap contributors",source_original_docente=False))
    print(f"Guardados {len(data):,} bytes en {path}")


if __name__=="__main__":
    main()
