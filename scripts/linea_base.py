#!/usr/bin/env python3
"""Línea base sin cliente TraCI, con macrodatos cada 900 segundos."""
import subprocess
import time
import xml.etree.ElementTree as ET
from entorno import ROOT, guardar_json


def main():
    out=ROOT/"salida/base"
    out.mkdir(parents=True,exist_ok=True)
    command=["sumo","-c",str(ROOT/"escenario/reto.sumocfg"),"--log",str(out/"sumo.log"),
             "--error-log",str(out/"sumo_avisos.log")]
    start=time.monotonic()
    with (out/"consola.log").open("w") as stream:
        subprocess.run(command,cwd=ROOT,check=True,stdout=stream,stderr=subprocess.STDOUT)
    root=ET.parse(out/"estadisticas.xml").getroot()
    result={e.tag:e.attrib for e in root}
    result["wall_seconds"]=time.monotonic()-start
    result["command"]=command
    guardar_json(out/"resumen.json",result)
    print(result)


if __name__=="__main__":
    main()
