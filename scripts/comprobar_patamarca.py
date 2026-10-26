#!/usr/bin/env python3
"""Reproduce la coordenada aportada y su distancia vial, sin ejecutar tráfico."""
import csv
import math
from entorno import ROOT, guardar_json, sha256
from reto_ambulancias import Hospital, traci, sumolib
import json


def decode11(code):
    """Centro y límites de un Plus Code completo de 11 caracteres significativos.

    Algoritmo público de Open Location Code: cinco pares base 20 y una celda
    de una cuadrícula de cinco filas y cuatro columnas. La recuperación del
    código corto con referencia Cuenca se conserva en los metadatos.
    https://github.com/google/open-location-code
    """
    alphabet = "23456789CFGHJMPQRVWX"
    if len(code) != 12 or code[8] != "+":
        raise ValueError("Se requiere un código completo de 11 dígitos")
    digits = [alphabet.index(c) for c in code.replace("+", "")]
    lat, lon = -90.0, -180.0
    for pair, scale in enumerate([20, 1, .05, .0025, .000125]):
        lat += digits[2 * pair] * scale
        lon += digits[2 * pair + 1] * scale
    dy, dx = .000125 / 5, .000125 / 4
    lat += (digits[10] // 4) * dy
    lon += (digits[10] % 4) * dx
    return dict(lat=round(lat + dy / 2, 12), lon=round(lon + dx / 2, 12),
                sur=round(lat, 12), norte=round(lat + dy, 12),
                oeste=round(lon, 12), este=round(lon + dx, 12))


def main():
    meta = json.loads((ROOT / "datos/patamarca_ubicacion.json").read_text())
    point = decode11(meta["codigo_completo"])
    with (ROOT / "datos/hospitales.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    row = next(r for r in rows if r["id"] == "MUNI_PATAMARCA")
    assert all(math.isclose(float(row[k]), point[k], abs_tol=1e-10, rel_tol=0)
               for k in ["lat", "lon"]), "La coordenada no corresponde al Plus Code"
    assert sha256(ROOT / meta["captura"]) == meta["captura_sha256"]
    out = ROOT / "salida/ubicacion"
    out.mkdir(parents=True, exist_ok=True)
    net = sumolib.net.readNet(str(ROOT / "escenario/cuenca_ciudad.net.xml"))
    traci.start(["sumo", "-n", str(ROOT / "escenario/cuenca_ciudad.net.xml"),
                 "-a", str(ROOT / "escenario/vtypes.add.xml"), "--no-step-log", "true",
                 "--error-log", str(out / "avisos.log")])
    try:
        hospitals = []
        for r in rows:
            h = Hospital(r["id"], r["nombre"], r["tipo"], float(r["lon"]), float(r["lat"]))
            h.ubicar(net, hospitals[0].edge if hospitals else None)
            hospitals.append(h)
        pat = next(h for h in hospitals if h.id == "MUNI_PATAMARCA")
        distances = []
        for lat in [point["sur"], point["norte"]]:
            for lon in [point["oeste"], point["este"]]:
                h = Hospital(f"ESQUINA_{len(distances)}", "Límite de celda", "publico", lon, lat)
                h.ubicar(net, hospitals[0].edge)
                distances.append(h.distancia_m)
        routes = sum(bool(traci.simulation.findRoute(a.edge, b.edge, vType="ambulance").edges)
                     for a in hospitals for b in hospitals)
        assert routes == 49
        assert all(h.distancia_m < 150 for h in hospitals)
        assert max(distances) < 150
        result = dict(codigo=meta["codigo_completo"], coordenada=point,
                      distancia_patamarca_m=pat.distancia_m, arista=pat.edge,
                      calle=pat.calle, distancia_maxima_esquinas_m=max(distances),
                      distancias_hospitales_m={h.id: h.distancia_m for h in hospitals},
                      pares_alcanzables=routes, cumple_A3=True,
                      hospitales_sha256=sha256(ROOT / "datos/hospitales.csv"),
                      red_sha256=sha256(ROOT / "escenario/cuenca_ciudad.net.xml"),
                      alcance="Ubicación de ficha cartográfica; no entrada de urgencias verificada")
        guardar_json(out / "patamarca.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        traci.close()


if __name__ == "__main__":
    main()
