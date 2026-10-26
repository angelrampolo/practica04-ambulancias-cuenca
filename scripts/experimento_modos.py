#!/usr/bin/env python3
"""Prueba causal aislada: misma pareja, misma vía; cambia solo speedMode."""
import subprocess
from entorno import ROOT, guardar_csv
import traci


def main():
    out=ROOT/"salida/modos"
    out.mkdir(parents=True,exist_ok=True)
    (out/"recta.nod.xml").write_text('<nodes><node id="a" x="0" y="0"/><node id="b" x="2000" y="0"/></nodes>')
    (out/"recta.edg.xml").write_text('<edges><edge id="recta" from="a" to="b" numLanes="1" speed="30"/></edges>')
    subprocess.run(["netconvert","-n",str(out/"recta.nod.xml"),"-e",str(out/"recta.edg.xml"),"-o",str(out/"recta.net.xml")],check=True)
    rows=[]
    for mode in [31,30,23,0]:
        with (out/f"modo_{mode}.log").open("w") as log:
            traci.start(["sumo","-n",str(out/"recta.net.xml"),"-a",str(ROOT/"escenario/vtypes.add.xml"),
                         "--collision.action","warn","--collision.mingap-factor","0",
                         "--time-to-teleport","-1","--seed","42","--no-step-log","true",
                         "--collision-output",str(out/f"modo_{mode}_colisiones.xml")],stdout=log)
            traci.route.add("ruta",["recta"])
            traci.vehicle.add("bus","ruta",typeID="bus",departPos="150",departSpeed="8")
            traci.vehicle.add("moto","ruta",typeID="moto",departPos="105",departSpeed="8")
            traci.simulationStep()
            traci.vehicle.setSpeed("bus",8)
            traci.vehicle.setSpeedMode("moto",mode)
            traci.vehicle.setLaneChangeMode("moto",0)
            traci.vehicle.setSpeed("moto",22)
            collision=None
            for _ in range(90):
                traci.simulationStep()
                cs=traci.simulation.getCollisions()
                if cs:
                    collision=cs[0]
                    break
            rows.append(dict(speedMode=mode,bit0=mode&1,colision=collision is not None,
                             tipo=collision.type if collision else "ninguna",t_s=traci.simulation.getTime()))
            if "moto" in traci.vehicle.getIDList():
                traci.vehicle.setSpeedMode("moto",31)
                traci.vehicle.setLaneChangeMode("moto",1621)
                traci.vehicle.setSpeed("moto",-1)
            traci.close()
    guardar_csv(out/"resultados.csv",rows)
    assert [r["colision"] for r in rows]==[False,True,False,True],rows
    print(rows)


if __name__=="__main__":
    main()
