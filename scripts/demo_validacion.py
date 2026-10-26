#!/usr/bin/env python3
"""Demostración A/B con el controlador real y captura de estados observados."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from entorno import ROOT, guardar_json, sha256
from reto_ambulancias import Simulacion, traci


class Demo(Simulacion):
    def __init__(self,automatico):
        super().__init__(SimpleNamespace(seed=42,tasa=5,p_sin=.25,retorno="cercano",end=12600,
            output=ROOT/"salida/visual/ejecucion",hospitales=ROOT/"datos/hospitales.csv",gui=True,gui_iniciar=True))
        self.automatico=automatico
        self.capturas={}
        self.pendiente=None
        self.view="View #0"
        self.retornos={}

    def iniciar(self):
        super().iniciar()
        # Solo cambia la vista, nunca las posiciones o la conducción.
        xs=[h.x for h in self.hospitales];ys=[h.y for h in self.hospitales]
        traci.gui.setBoundary(self.view,min(xs)-500,min(ys)-500,max(xs)+500,max(ys)+500)

    def capturar(self,name,data,x=None,y=None):
        if x is not None:
            traci.gui.setBoundary(self.view,x-170,y-130,x+170,y+130)
        else:
            xs=[h.x for h in self.hospitales];ys=[h.y for h in self.hospitales]
            traci.gui.setBoundary(self.view,min(xs)-500,min(ys)-500,max(xs)+500,max(ys)+500)
        path=ROOT/"salida/visual"/(name+".png")
        # SUMO escribe la captura durante el siguiente paso, no al solicitarla.
        if path.exists():
            path.unlink()
        traci.gui.screenshot(self.view,str(path))
        self.pendiente=(name,path,dict(t_s=self.t,**data))

    def cerrar(self,a):
        h=self.by_id[a.hospital_retorno]
        before=len(h.cola)
        super().cerrar(a)
        self.retornos[a.id]=dict(t_disponible=self.t,stock_antes=before,stock_despues=len(h.cola))

    def verificar_flota(self):
        super().verificar_flota()
        if self.pendiente:
            name,path,data=self.pendiente
            if path.exists():
                data["archivo"]=str(path.relative_to(ROOT))
                data["sha256"]=sha256(path)
                self.capturas[name]=data
                self.pendiente=None
                print("\nDEMOSTRACIÓN",name,json.dumps(data,ensure_ascii=False),flush=True)
                if not self.automatico:
                    input("Revisa SUMO-GUI por VNC. Pulsa Enter aquí para continuar... ")
            return
        if "01_hospitales" not in self.capturas:
            if self.t<10:
                return
            self.capturar("01_hospitales",dict(pois=list(traci.poi.getIDList()),
                hospitales=len(self.hospitales),stock={h.id:len(h.cola) for h in self.hospitales}))
            return
        ids=set(traci.vehicle.getIDList())
        if "02_accidente_cola" not in self.capturas:
            for a in self.accs:
                if a.estado not in ["en_camino","atendiendo","espera"] or not {a.bus,a.moto}<=ids:
                    continue
                stopped=[v for v in traci.edge.getLastStepVehicleIDs(a.edge)
                    if v not in [a.bus,a.moto] and not v.startswith("amb_")
                    and traci.vehicle.getLaneID(v)==traci.vehicle.getLaneID(a.bus)
                    and traci.vehicle.getSpeed(v)<.1
                    and 0<=a.pos-traci.vehicle.getLanePosition(v)<=350]
                if stopped and traci.vehicle.getSpeed(a.bus)<.1 and traci.vehicle.getSpeed(a.moto)<.1:
                    self.capturar("02_accidente_cola",dict(accidente=a.id,edge=a.edge,
                        bus=a.bus,moto=a.moto,vel_bus=traci.vehicle.getSpeed(a.bus),
                        vel_moto=traci.vehicle.getSpeed(a.moto),cola=stopped,estado=a.estado),a.x,a.y)
                    return
        if "02_accidente_cola" in self.capturas and "03_retorno" not in self.capturas:
            for a in self.accs:
                if a.estado=="cerrado" and a.t_disponible==self.t and a.hospital_origen!=a.hospital_retorno:
                    h=self.by_id[a.hospital_retorno]
                    if a.unidad not in h.cola:
                        continue
                    self.capturar("03_retorno",dict(accidente=a.id,unidad=a.unidad,
                        origen=a.hospital_origen,destino=h.id,stock_destino=len(h.cola),
                        unidad_en_cola=a.unidad in h.cola,**self.retornos[a.id]),h.x,h.y)
                    return

    def exportar(self):
        super().exportar()
        complete=all(k in self.capturas for k in ["01_hospitales","02_accidente_cola","03_retorno"])
        guardar_json(ROOT/"salida/visual/verificacion_visual.json",dict(
            sumo=self.version,seed=42,capturas=self.capturas,
            controles_visuales_observados=complete,
            controlador_sha256=sha256(ROOT/"scripts/reto_ambulancias.py"),
            demo_sha256=sha256(Path(__file__)),
            red_sha256=sha256(ROOT/"escenario/cuenca_ciudad.net.xml"),
            hospitales_sha256=sha256(ROOT/"datos/hospitales.csv"),
            demostracion_ante_docente="Pendiente: debe realizarla el estudiante en su evaluación"))
        if not complete:
            raise RuntimeError("No se observaron todos los estados visuales; consultar el log")
        print("Comprobación SUMO-GUI completa; evidencias en salida/visual/",flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--automatico",action="store_true",help="Ejecutar la misma demo sin pausas de teclado")
    args=p.parse_args()
    Demo(args.automatico).ejecutar()


if __name__=="__main__":
    main()
