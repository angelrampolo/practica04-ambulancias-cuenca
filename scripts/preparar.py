#!/usr/bin/env python3
"""F0 y F1: derivación trazable de la red y demanda reproducible de 3 horas."""
import argparse
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from entorno import ROOT, SUMO_HOME, guardar_csv, guardar_json, sha256
import sumolib

ESC = ROOT / "escenario"
TYPES = ",".join("highway." + t for t in (
    "motorway", "motorway_link", "trunk", "trunk_link", "primary",
    "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link"))


def run(command, name):
    log = ROOT / "salida/preparacion" / (name + ".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    print("Ejecutando:", " ".join(map(str, command)), flush=True)
    with log.open("w") as out:
        subprocess.run(list(map(str, command)), cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, check=True)
    return list(map(str, command))


def contar(path):
    net = sumolib.net.readNet(str(path))
    edges = net.getEdges()
    # Componentes débiles: no confundir con accesibilidad dirigida por vClass.
    unseen = {e.getID() for e in edges}
    components = []
    while unseen:
        stack = [net.getEdge(unseen.pop())]
        size = 0
        while stack:
            edge = stack.pop()
            size += 1
            for node in (edge.getFromNode(), edge.getToNode()):
                for nxt in node.getIncoming() + node.getOutgoing():
                    if nxt.getID() in unseen:
                        unseen.remove(nxt.getID())
                        stack.append(nxt)
        components.append(size)
    return dict(red=path.name, aristas=len(edges), nodos=len(net.getNodes()),
                semaforos=len(net.getTrafficLights()), km_arista=sum(e.getLength() for e in edges)/1000,
                km_carril=sum(e.getLength()*e.getLaneNumber() for e in edges)/1000,
                componentes_debiles=len(components))


def red(source):
    target = ESC / "cuenca_ciudad.net.xml"
    original = ROOT / "datos/cuenca_net.xml"
    if source.resolve() != original.resolve():
        shutil.copy2(source, original)
    command = run(["netconvert", "-s", original, "-o", target,
        "--keep-edges.by-type", TYPES,
        "--keep-edges.in-geo-boundary", "-79.030,-2.930,-78.950,-2.860",
        "--keep-edges.components", "1", "--remove-edges.isolated",
        "--geometry.remove", "--junctions.join", "--junctions.join-dist", "25",
        "--no-turnarounds.except-deadend"], "netconvert")
    rows = [contar(original), contar(target)]
    for r in rows:
        r["fraccion_aristas"] = r["aristas"] / rows[0]["aristas"]
        r["fraccion_km"] = r["km_arista"] / rows[0]["km_arista"]
    guardar_csv(ROOT / "salida/preparacion/redes.csv", rows)
    guardar_json(ROOT / "salida/preparacion/red.json", {
        "source": str(source), "source_sha256": sha256(original),
        "derived_sha256": sha256(target), "command": command, "networks": rows})


def demanda(seed):
    rows = []
    for typ, cls, rate, prefix in [("car","passenger",1200,"car"),
                                   ("bus","bus",100,"bus"),
                                   ("moto","motorcycle",300,"moto")]:
        route = ESC / f"fondo_{typ}.rou.xml"
        run(["python3", SUMO_HOME / "tools/randomTrips.py", "-n", ESC / "cuenca_ciudad.net.xml",
             "-o", ESC / f"fondo_{typ}.trips.xml", "-r", route,
             "-a", ESC / "vtypes.add.xml", "--trip-attributes", f'type="{typ}" departLane="best" departSpeed="max"',
             "--vclass", cls, "--prefix", prefix, "--seed", seed,
             "--begin", "0", "--end", "10800", "--period", 3600/rate,
             "--validate"], f"demanda_{typ}")
        tree = ET.parse(route)
        for vt in tree.getroot().findall("vType"):
            tree.getroot().remove(vt)
        tree.write(route, encoding="utf-8", xml_declaration=True)
        rows.append(dict(tipo=typ, veh_h=rate, solicitados=rate*3,
                         validos=len(tree.getroot().findall("vehicle")), semilla=seed,
                         sha256=sha256(route)))
    guardar_csv(ROOT / "salida/preparacion/demanda.csv", rows)
    print(json.dumps(rows, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paso", choices=["red", "demanda", "todo"])
    p.add_argument("--source", type=Path, default=ROOT / "datos/cuenca_net.xml")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    if args.paso in ["red", "todo"]:
        red(args.source)
    if args.paso in ["demanda", "todo"]:
        demanda(args.seed)


if __name__ == "__main__":
    main()
