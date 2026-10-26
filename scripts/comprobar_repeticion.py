#!/usr/bin/env python3
"""Reproducibilidad semántica exacta: resultados CSV y eventos, sin reloj de pared."""
from entorno import ROOT, sha256, guardar_json


def main():
    files=["accidentes.csv","hospitales.csv","decisiones.csv","stock_tiempo.csv",
           "hospitales_ubicados.csv","eventos.jsonl","conectividad_hospitales.csv"]
    rows=[]
    for file in files:
        a=sha256(ROOT/"salida/principal"/file)
        b=sha256(ROOT/"salida/repeticion"/file)
        rows.append(dict(archivo=file,principal_sha256=a,repeticion_sha256=b,identico=a==b))
    guardar_json(ROOT/"salida/reproducibilidad.json",rows)
    for row in rows:
        print(row["archivo"],"IDÉNTICO" if row["identico"] else "DIFERENTE")
    if not all(r["identico"] for r in rows):
        raise SystemExit(1)


if __name__=="__main__":
    main()
