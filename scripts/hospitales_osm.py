#!/usr/bin/env python3
"""Extrae los siete hospitales del XML OSM archivado, con referencia de origen."""
import xml.etree.ElementTree as ET
import json
from entorno import ROOT, guardar_csv


def main():
    r=ET.parse(ROOT/"datos/cuenca_osm.xml").getroot()
    nodes={n.get("id"):(float(n.get("lon")),float(n.get("lat"))) for n in r.findall("node")}
    specs=[("VCM","Hospital Vicente Corral Moscoso","publico","way","48591686"),
           ("IESS","Hospital José Carrasco Arteaga","publico","way","109187251"),
           ("MILITAR","Hospital Militar","publico","way","388587975"),
           ("MUNI_PATAMARCA","Hospital Municipal del Niño y la Mujer","publico","way","379757480"),
           ("MUNI_VALLE","Hospital Básico Municipal de El Valle","publico","node","13235900594"),
           ("MONTE_SINAI","Hospital Monte Sinaí","privado","way","374845885"),
           ("DEL_RIO","Hospital Universitario del Río","privado","way","433553788")]
    rows=[]
    for ident,name,kind,typ,ref in specs:
        if typ=="node":
            lon,lat=nodes[ref]
            method="nodo OSM"
        else:
            e=r.find(f"way[@id='{ref}']")
            pts=[nodes[n.get("ref")] for n in e.findall("nd")]
            # Centroide de área en coordenadas locales para evitar cancelación.
            ox,oy=pts[0]
            pts=[(x-ox,y-oy) for x,y in pts]
            pairs=list(zip(pts,pts[1:]+pts[:1]))
            cross=[x*v-u*y for (x,y),(u,v) in pairs]
            area2=sum(cross)
            lon=ox+sum((p[0]+q[0])*c for (p,q),c in zip(pairs,cross))/(3*area2)
            lat=oy+sum((p[1]+q[1])*c for (p,q),c in zip(pairs,cross))/(3*area2)
            method="centroide del polígono OSM (aproximación plana local)"
        rows.append(dict(id=ident,nombre=name,tipo=kind,lon=f"{lon:.8f}",lat=f"{lat:.8f}",
                         fuente=f"https://www.openstreetmap.org/{typ}/{ref}",metodo=method))
    correction=ROOT/"datos/patamarca_ubicacion.json"
    if correction.exists():
        update=json.loads(correction.read_text())["coordenada_actual"]
        next(row for row in rows if row["id"]==update["id"]).update(update)
    guardar_csv(ROOT/"datos/hospitales.csv",rows)


if __name__=="__main__":
    main()
