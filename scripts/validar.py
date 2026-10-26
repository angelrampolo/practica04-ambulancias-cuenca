#!/usr/bin/env python3
"""Auditoría independiente de CSV, XML SUMO, inventario y trazabilidad."""
import argparse
import csv
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from entorno import ROOT, guardar_json, sha256


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def validar(folder,principal=False):
    checks=[]
    def check(name,passed,detail="",level="error"):
        checks.append(dict(prueba=name,ok=bool(passed),detalle=detail,nivel=level))
    a=read(folder/"accidentes.csv")
    h=read(folder/"hospitales.csv")
    located=read(folder/"hospitales_ubicados.csv")
    p=json.loads((folder/"parametros.json").read_text())
    execution=json.loads((folder/"ejecucion.json").read_text())
    check("Controlador coincide con la ejecución",sha256(ROOT/"scripts/reto_ambulancias.py")==p["controlador_sha256"])
    check("Hospitales coinciden con la ejecución",sha256(ROOT/"datos/hospitales.csv")==p["hospitales_sha256"])
    check("Entradas SUMO coinciden con la ejecución",all(sha256(ROOT/"escenario"/name)==digest for name,digest in p["sha256"].items()))
    check("Red de origen coincide con la ejecución",sha256(ROOT/"datos/cuenca_net.xml")==p["red_origen_sha256"])
    statistics=ET.parse(folder/"estadisticas.xml").getroot()
    tele=statistics.find("teleports")
    check("Sin teleportación (TraCI y estadística SUMO)",execution["teleports"]==0 and int(tele.get("total"))==0)
    check("Siete hospitales",len(h)==len(located)==7)
    maxdistance=max(float(row["distancia_m"]) for row in located)
    check("Distancia de hospitales <150 m",maxdistance<150,f"Máxima: {maxdistance:.2f} m",level="advertencia")
    reach=read(folder/"conectividad_hospitales.csv")
    check("Conectividad dirigida emergency: 49 pares",len(reach)==49 and all(r["alcanzable"]=="True" for r in reach))
    check("Algún hospital con stock inicial cero",any(int(row["stock_inicial"])==0 for row in h),level="advertencia")
    stock0=sum(int(row["stock_inicial"]) for row in h)
    stock1=sum(int(row["stock_final"]) for row in h)
    busy=[row for row in a if row["unidad"] and row["estado"]!="cerrado"]
    check("Conservación global de flota",stock0==stock1+len(busy)==p["fleet"],f"Inicial={stock0}; final={stock1}; en misión={len(busy)}")
    check("No hay ambulancias duplicadas en misión",len({row["unidad"] for row in busy})==len(busy))
    for row in h:
        hid=row["hospital"]
        dispatches=sum(r["hospital_origen"]==hid for r in a)
        returns=sum(r["hospital_retorno"]==hid and r["estado"]=="cerrado" for r in a)
        check(f"Balance local {hid}",int(row["stock_final"])==int(row["stock_inicial"])-dispatches+returns
              and int(row["despachos"])==dispatches and int(row["recibidas"])==returns)
        check(f"Utilización bien definida {hid}",bool(row["utilizacion_ref_pct"])==(int(row["stock_inicial"])>0))
    check("Identificadores de accidentes únicos",len({r["id"] for r in a})==len(a))
    check("Parejas bus–moto únicas",len({tuple(sorted([r["bus"],r["moto"]])) for r in a})==len(a))
    collision_pairs={tuple(sorted([c.get("collider"),c.get("victim")])) for c in ET.parse(folder/"colisiones.xml").getroot().findall("collision")}
    check("Cada accidente tiene una colisión física en XML",all(tuple(sorted([r["bus"],r["moto"]])) in collision_pairs for r in a))
    temporal=True
    for row in a:
        ts=[float(row[k]) for k in ["t_accidente","t_despacho","t_llegada","t_retorno","t_disponible"]]
        observed=[t for t in ts if t>=0]
        temporal &= observed==sorted(observed)
        if row["estado"]=="cerrado":
            temporal &= ts[3]-ts[2]>=120
            temporal &= math.isclose(float(row["respuesta_total_s"]),float(row["espera_s"])+float(row["desplazamiento_s"]))
            temporal &= math.isclose(float(row["respuesta_total_s"]),ts[2]-ts[0])
            temporal &= math.isclose(float(row["mision_s"]),ts[4]-ts[1])
    check("Cronología, atención 120 s e identidades de tiempos",temporal)
    check("Ninguna misión queda abierta",all(r["estado"]=="cerrado" for r in a),level="error" if principal else "advertencia")
    check("Vaciado: ningún vehículo restante",execution["running_final"]==execution["expected_final"]==0,
          f"Activos={execution['running_final']}; esperados={execution['expected_final']}",level="advertencia")
    decisions=read(folder/"decisiones.csv")
    check("Negativas aleatorias observadas",any(r["resultado"]=="negativa_aleatoria" for r in decisions),level="advertencia")
    for r in decisions:
        if r["resultado"]=="despacho":
            prior=[d for d in decisions if d["t"]==r["t"] and d["accidente"]==r["accidente"] and int(d["rango"])<int(r["rango"])]
            check(f"Elección por ETA {r['accidente']}",all(d["resultado"] in ["sin_stock","negativa_aleatoria"] and float(d["eta_s"])<=float(r["eta_s"])+1e-8 for d in prior))
    if principal:
        check("B1: 15 ± 2 accidentes",13<=len(a)<=17,f"Observados={len(a)}")
        check("B1: lugares distintos",len({r["edge"] for r in a})==len(a),level="advertencia")
        check("B2: despacho fuera del hospital más rápido",any(int(r["rango_hospital"])>1 for r in a))
        check("B3: retorno a hospital diferente",any(r["hospital_origen"]!=r["hospital_retorno"] for r in a if r["estado"]=="cerrado"))
        check("B3: aumenta el stock de algún hospital",any(int(r["stock_final"])>int(r["stock_inicial"]) for r in h))
    result=dict(carpeta=folder.name,pruebas=checks,errores=sum(not c["ok"] and c["nivel"]=="error" for c in checks),
                advertencias=sum(not c["ok"] and c["nivel"]=="advertencia" for c in checks))
    guardar_json(folder/"validacion.json",result)
    return result


def validar_escenario():
    rows=[]
    def check(name,ok,detail="",level="error"):
        rows.append(dict(prueba=name,ok=bool(ok),detalle=detail,nivel=level))
    source=json.loads((ROOT/"datos/procedencia_red.json").read_text())
    check("A1: red original del ZIP docente",source["tipo"]=="red_docente_aportada_por_usuario" and
          sha256(ROOT/"datos/cuenca_net.xml")==source["red_sha256"] and
          sha256(ROOT/source["archivo_zip"])==source["zip_sha256"])
    preparation=json.loads((ROOT/"salida/preparacion/red.json").read_text())
    check("F0: red derivada trazable",sha256(ROOT/"datos/cuenca_net.xml")==preparation["source_sha256"] and
          sha256(ROOT/"escenario/cuenca_ciudad.net.xml")==preparation["derived_sha256"])
    networks=read(ROOT/"salida/preparacion/redes.csv")
    check("A1: una componente débil y semáforos",int(networks[1]["componentes_debiles"])==1 and int(networks[1]["semaforos"])>0)
    cfg=ET.parse(ROOT/"escenario/reto.sumocfg").getroot()
    check("A2: teleport desactivado y colisión warn",all(cfg.find(".//"+key).get("value")==value for key,value in [
        ("time-to-teleport","-1"),("time-to-teleport.disconnected","-1"),("collision.action","warn"),
        ("collision.check-junctions","true"),("collision.mingap-factor","0"),("step-length","1"),("end","12600")]))
    stats=ET.parse(ROOT/"salida/base/estadisticas.xml").getroot()
    check("A2: >=4500 insertados",int(stats.find("vehicles").get("inserted"))>=4500)
    check("A2: línea base sin teleports",int(stats.find("teleports").get("total"))==0)
    check("A2: línea base vacía al cierre",int(stats.find("vehicles").get("running"))==0)
    trips=ET.parse(ROOT/"salida/base/tripinfo.xml").getroot().findall("tripinfo")
    check("A2: tres clases circulan",{e.get("vType") for e in trips}=={"car","bus","moto"})
    intervals=ET.parse(ROOT/"salida/base/macro.xml").getroot().findall("interval")
    check("F1.4: 14 intervalos de 900 s",len(intervals)==14 and all(float(e.get("end"))-float(e.get("begin"))==900 for e in intervals))
    modes=read(ROOT/"salida/modos/resultados.csv")
    check("F3: experimento 31/30/23/0",{int(r["speedMode"]):r["colision"] for r in modes}=={31:"False",30:"True",23:"False",0:"True"})
    replay=ROOT/"salida/reproducibilidad.json"
    if replay.exists():
        check("A4: siete salidas idénticas al repetir",all(r["identico"] and
            sha256(ROOT/"salida/principal"/r["archivo"])==r["principal_sha256"] and
            sha256(ROOT/"salida/repeticion"/r["archivo"])==r["repeticion_sha256"]
            for r in json.loads(replay.read_text())))
    visual_path=ROOT/"salida/visual/verificacion_visual.json"
    visual_ok=False
    if visual_path.exists():
        v=json.loads(visual_path.read_text())
        captures=v.get("capturas",{})
        accident=captures.get("02_accidente_cola",{})
        arrival=captures.get("03_retorno",{})
        visual_ok=(v.get("controles_visuales_observados",False)
            and v.get("red_sha256")==sha256(ROOT/"escenario/cuenca_ciudad.net.xml")
            and v.get("hospitales_sha256")==sha256(ROOT/"datos/hospitales.csv")
            and v.get("controlador_sha256")==sha256(ROOT/"scripts/reto_ambulancias.py")
            and v.get("demo_sha256")==sha256(ROOT/"scripts/demo_validacion.py")
            and len(captures)==3 and all((ROOT/c["archivo"]).is_file()
                and c.get("sha256")==sha256(ROOT/c["archivo"]) for c in captures.values())
            and len(captures.get("01_hospitales",{}).get("pois",[]))==7
            and accident.get("vel_bus")==accident.get("vel_moto")==0
            and bool(accident.get("cola"))
            and arrival.get("origen")!=arrival.get("destino")
            and arrival.get("unidad_en_cola",False)
            and arrival.get("stock_despues",-1)==arrival.get("stock_antes",-3)+1)
    check("GUI: evidencia vigente de hospitales, cola y retorno",visual_ok,
          "La demostración y calificación ante el docente corresponden al estudiante",level="advertencia")
    result=dict(carpeta="escenario",pruebas=rows,errores=sum(not r["ok"] and r["nivel"]=="error" for r in rows),
                advertencias=sum(not r["ok"] and r["nivel"]=="advertencia" for r in rows))
    guardar_json(ROOT/"salida/validacion_escenario.json",result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,default=ROOT/"salida/principal")
    p.add_argument("--todos",action="store_true")
    args=p.parse_args()
    paths=sorted((ROOT/"salida").glob("*/accidentes.csv")) if args.todos else [args.folder/"accidentes.csv"]
    results=[validar(path.parent,path.parent.name=="principal") for path in paths if path.parent.name!="smoke"]
    if args.todos:
        results.insert(0,validar_escenario())
    for r in results:
        print(f"{r['carpeta']}: {len(r['pruebas'])} controles, {r['errores']} errores, {r['advertencias']} advertencias")
        for c in r["pruebas"]:
            if not c["ok"]:
                print(f"  {c['nivel']}: {c['prueba']} {c['detalle']}")
    guardar_json(ROOT/"salida/validacion_global.json",results)
    sys.exit(1 if any(r["errores"] for r in results) else 0)


if __name__=="__main__":
    main()
