#!/usr/bin/env python3
"""F2–F5. Control TraCI, accidentes observados y flota conservada por unidad.

Las horas de agenda, colisión, despacho, llegada y disponibilidad se guardan
por separado. Nunca se inventa una llegada ni se descarta una misión censurada.
"""
import argparse
import csv
import datetime
import heapq
import math
import random
import subprocess
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path

from entorno import ROOT, guardar_csv, guardar_json, sha256
import traci
import sumolib


def agenda_accidentes(seed, tasa=5):
    rng = random.Random(seed + 1)
    return sorted(math.ceil(h*3600 + rng.uniform(300, 3480))
                  for h in range(3) for _ in range(tasa))


def restaurar(veh):
    traci.vehicle.setSpeedMode(veh, 31)
    traci.vehicle.setLaneChangeMode(veh, 1621)
    traci.vehicle.setSpeed(veh, -1)


@dataclass
class Hospital:
    id: str
    nombre: str
    tipo: str
    lon: float
    lat: float
    edge: str = ""
    pos: float = 0
    lane: int = 0
    x: float = 0
    y: float = 0
    distancia_m: float = 0
    edge_convertRoad: str = ""
    distancia_convertRoad_m: float = 0
    calle: str = ""
    stock_ini: int = 0
    cola: deque = field(default_factory=deque)
    despachos: int = 0
    recibidas: int = 0
    rechazos: int = 0
    sin_stock: int = 0
    ocupado_s: float = 0
    ocupado_3h_s: float = 0

    def ubicar(self, net, anchor=None):
        self.edge, self.pos, self.lane = traci.simulation.convertRoad(
            self.lon, self.lat, isGeo=True, vClass="emergency")
        self.x, self.y = traci.simulation.convertGeo(self.lon, self.lat, fromGeo=True)
        rx, ry = traci.simulation.convert2D(self.edge, self.pos, laneIndex=self.lane)
        self.distancia_m = math.hypot(rx-self.x, ry-self.y)
        self.edge_convertRoad = self.edge
        self.distancia_convertRoad_m = self.distancia_m
        # Una componente débil no garantiza accesibilidad en ambos sentidos.
        # La importación OSM alternativa contiene ramales sin conexión de vuelta.
        def connected(edge):
            return anchor is None or all(traci.simulation.findRoute(src,dst,vType="ambulance").edges
                                         for src,dst in [(anchor,edge),(edge,anchor)])
        if not connected(self.edge):
            candidates=[]
            for edge in net.getEdges():
                for lane in edge.getLanes():
                    if lane.allows("emergency"):
                        pos,dist=sumolib.geomhelper.polygonOffsetAndDistanceToPoint((self.x,self.y),lane.getShape())
                        candidates.append((dist,edge.getID(),pos,lane.getIndex()))
            for dist,edge,pos,lane in sorted(candidates):
                if connected(edge):
                    self.edge,self.pos,self.lane,self.distancia_m=edge,pos,lane,dist
                    break
            else:
                raise RuntimeError(f"No hay acceso bidireccional para {self.id}")
        self.calle = net.getEdge(self.edge).getName()
        traci.poi.add("H_"+self.id, self.x, self.y, (210,45,65,255), poiType="hospital")


@dataclass
class Accidente:
    id: str
    t_accidente: float
    bus: str
    moto: str
    edge: str
    pos: float
    x: float
    y: float
    tipo_colision: str
    plan_id: int = 0
    t_programado: float = -1
    estado: str = "espera"
    hospital_origen: str = ""
    hospital_retorno: str = ""
    unidad: str = ""
    vehiculo: str = ""
    t_despacho: float = -1
    t_llegada: float = -1
    t_retorno: float = -1
    t_disponible: float = -1
    eta_s: float = -1
    ruta_m: float = -1
    rango_hospital: int = 0
    criterio_llegada: str = ""
    proximo_intento: float = 0


class Simulacion:
    def __init__(self, args):
        self.args = args
        self.out = args.output.resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.logfile = (self.out / "eventos.log").open("w", buffering=1)
        self.events = (self.out / "eventos.jsonl").open("w", buffering=1)
        self.rng = random.Random(args.seed+2)
        self.disponibilidad = random.Random(args.seed+3)
        self.accs = []
        self.hospitales = []
        self.pending = {}
        self.seen = set()
        self.stopping = {}
        self.used_edges = set()
        self.teleports = 0
        self.removed_background = set()
        self.attempts = 0
        self.t = 0
        self.decisions = []
        self.stocks = []
        self.accesibilidad = {}
        self.agenda = agenda_accidentes(args.seed, args.tasa)
        self.queue = [(t, i+1) for i, t in enumerate(self.agenda)]
        heapq.heapify(self.queue)

    def log(self, kind, message, **data):
        import json
        self.logfile.write(f"[{self.t:6.0f} s] {kind} {message}\n")
        self.events.write(json.dumps(dict(t=self.t, evento=kind, detalle=message, **data), ensure_ascii=False)+"\n")

    def iniciar(self):
        self.started = time.monotonic()
        cfg = ROOT / "escenario/reto.sumocfg"
        command = ["sumo-gui" if self.args.gui else "sumo", "-c", str(cfg),
                   "--additional-files", str(ROOT / "escenario/vtypes.add.xml"),
                   "--seed", str(self.args.seed), "--end", str(self.args.end),
                   "--tripinfo-output", str(self.out/"tripinfo.xml"),
                   "--collision-output", str(self.out/"colisiones.xml"),
                   "--statistic-output", str(self.out/"estadisticas.xml"),
                   "--summary-output", str(self.out/"summary.xml"),
                   "--log", str(self.out/"sumo.log"),
                   "--error-log", str(self.out/"sumo_avisos.log")]
        if self.args.gui:
            command += ["--gui-settings-file",str(ROOT/"scripts/vista.gui.xml"),"--quit-on-end"]
            if getattr(self.args,"gui_iniciar",False):
                command += ["--start"]
        self.console = (self.out / "sumo_console.log").open("w")
        traci.start(command, stdout=self.console)
        self.version = traci.getVersion()
        self.net = sumolib.net.readNet(str(ROOT/"escenario/cuenca_ciudad.net.xml"))
        self.length = {e.getID(): e.getLength() for e in self.net.getEdges()}
        fleet_rng = random.Random(self.args.seed)
        unit = 1
        with self.args.hospitales.open() as stream:
            for row in csv.DictReader(stream):
                h = Hospital(row["id"], row["nombre"], row["tipo"], float(row["lon"]), float(row["lat"]))
                h.ubicar(self.net,self.hospitales[0].edge if self.hospitales else None)
                h.stock_ini = fleet_rng.randint(1,3) if h.tipo == "publico" else fleet_rng.randint(0,1)
                h.cola = deque(f"U{n:02d}" for n in range(unit, unit+h.stock_ini))
                unit += h.stock_ini
                self.hospitales.append(h)
                self.log("HOSPITAL", f"{h.id} {h.tipo} -> {h.edge} | {h.calle} | {h.distancia_m:.1f} m | stock {h.stock_ini}")
        self.fleet = unit-1
        self.by_id = {h.id:h for h in self.hospitales}
        guardar_csv(self.out/"hospitales_ubicados.csv", [dict(id=h.id,nombre=h.nombre,tipo=h.tipo,
            lon=h.lon,lat=h.lat,edge=h.edge,pos=h.pos,lane=h.lane,calle=h.calle,
            distancia_m=h.distancia_m,edge_convertRoad=h.edge_convertRoad,
            distancia_convertRoad_m=h.distancia_convertRoad_m,x=h.x,y=h.y,stock_ini=h.stock_ini) for h in self.hospitales])
        guardar_json(self.out/"parametros.json", {
            "seed": self.args.seed, "tasa": self.args.tasa, "p_sin": self.args.p_sin,
            "retorno": self.args.retorno, "end": self.args.end,
            "agenda": self.agenda, "sumo": self.version, "command": command,
            "fleet": self.fleet, "demanda_h": 3, "atencion_s": 120,
            "fecha_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "red_origen_sha256":sha256(ROOT/"datos/cuenca_net.xml"),
            "hospitales_sha256":sha256(self.args.hospitales),
            "controlador_sha256":sha256(Path(__file__)),
            "sha256": {p.name:sha256(p) for p in sorted((ROOT/"escenario").glob("*")) if p.is_file()}})
        self.log("AGENDA", f"{len(self.agenda)} instantes: {self.agenda}; flota={self.fleet}")
        reachability=[]
        for h in self.hospitales:
            for g in self.hospitales:
                r=traci.simulation.findRoute(h.edge,g.edge,vType="ambulance")
                reachability.append(dict(origen=h.id,destino=g.id,alcanzable=bool(r.edges),eta_libre_s=r.travelTime))
        guardar_csv(self.out/"conectividad_hospitales.csv",reachability)

    def parar(self, veh):
        traci.vehicle.setSpeedMode(veh, 0)
        traci.vehicle.setLaneChangeMode(veh, 0)
        traci.vehicle.setSpeed(veh, 0)
        self.stopping[veh] = self.t+1

    def programar_accidente(self, plan_id, ids):
        busy = {a.bus for a in self.accs} | {v["bus"] for v in self.pending.values()}
        candidates = []
        for veh in sorted(ids):
            if not veh.startswith("bus") or veh in busy:
                continue
            e = traci.vehicle.getRoadID(veh)
            if e.startswith(":") or e in self.used_edges:
                continue
            pos = traci.vehicle.getLanePosition(veh)
            speed = traci.vehicle.getSpeed(veh)
            if 4 <= speed < 18 and pos > 60 and self.length.get(e, 0)-pos > speed*(45/(22-speed)+2)+25:
                if e not in self.accesibilidad:
                    anchor=self.hospitales[0].edge
                    self.accesibilidad[e]=all(traci.simulation.findRoute(src,dst,vType="ambulance").edges
                        for src,dst in [(anchor,e),(e,anchor)])
                    if not self.accesibilidad[e]:
                        self.log("ARISTA_NO_SERVIBLE",f"{e}: no hay ida y retorno emergency; no se programa un choque aquí")
                if self.accesibilidad[e]:
                    candidates.append(veh)
        if not candidates:
            heapq.heappush(self.queue, (self.t+20,plan_id))
            self.log("REPROGRAMAR", f"plan {plan_id}: sin bus apto; +20 s")
            return
        bus = self.rng.choice(candidates)
        self.attempts += 1
        moto = f"imprudente_{plan_id}_{self.attempts}"
        route = traci.vehicle.getRoute(bus)[traci.vehicle.getRouteIndex(bus):]
        route_id = "ruta_"+moto
        traci.route.add(route_id, route)
        traci.vehicle.add(moto, route_id, typeID="moto", depart="now",
                          departLane=str(traci.vehicle.getLaneIndex(bus)),
                          departPos=str(traci.vehicle.getLanePosition(bus)-45), departSpeed="max")
        self.pending[moto] = dict(bus=bus,t=self.t,plan_id=plan_id,armed=False,
                                  edge=traci.vehicle.getRoadID(bus))
        self.log("IMPRUDENTE", f"{moto} persigue a {bus}; plan {plan_id}")

    def reprogramar(self, moto, reason, ids):
        pending = self.pending.pop(moto)
        if moto in ids:
            restaurar(moto)
            traci.vehicle.remove(moto)
            ids.discard(moto)
        else:
            # También cancela una inserción que sigue esperando hueco en SUMO.
            try:
                traci.vehicle.remove(moto)
            except traci.TraCIException:
                pass
        heapq.heappush(self.queue, (self.t+60,pending["plan_id"]))
        self.log("REPROGRAMAR", f"{moto}: {reason}; +60 s")

    def detectar_colisiones(self, ids):
        for c in traci.simulation.getCollisions():
            pair = tuple(sorted([c.collider,c.victim]))
            if pair in self.seen:
                continue
            self.seen.add(pair)
            members = [v for v in pair if v in ids]
            kinds = {v:traci.vehicle.getVehicleClass(v) for v in members}
            protected = {v for a in self.accs if a.estado != "cerrado" for v in [a.bus,a.moto,a.vehiculo]}
            if set(kinds.values()) == {"bus","motorcycle"} and not (set(pair)&protected):
                bus = next(v for v in members if kinds[v]=="bus")
                moto = next(v for v in members if kinds[v]=="motorcycle")
                edge = traci.vehicle.getRoadID(bus)
                pos = traci.vehicle.getLanePosition(bus)
                x,y = traci.vehicle.getPosition(bus)
                if edge.startswith(":"):
                    route = traci.vehicle.getRoute(bus)
                    idx = min(traci.vehicle.getRouteIndex(bus)+1, len(route)-1)
                    edge, pos = route[idx], 0
                pos = max(0,min(pos,self.length[edge]-.1))
                plan = self.pending.pop(moto, {})
                a = Accidente(f"ACC{len(self.accs)+1:02d}",self.t,bus,moto,edge,pos,x,y,c.type,
                              plan_id=plan.get("plan_id",0),
                              t_programado=self.agenda[plan["plan_id"]-1] if plan else -1)
                self.accs.append(a)
                self.used_edges.add(edge)
                for v in [bus,moto]:
                    self.parar(v)
                    traci.vehicle.setColor(v,(230,55,65,255))
                traci.poi.add(a.id,x,y,(255,180,30,255),poiType="accidente")
                self.log("ACCIDENTE", f"{a.id} {c.type} {bus} x {moto} en {edge}",accidente=a.id)
            else:
                removed = []
                for v in members:
                    if v not in protected and kinds[v] != "emergency":
                        traci.vehicle.remove(v)
                        ids.discard(v)
                        self.removed_background.add(v)
                        removed.append(v)
                self.log("COLISION_FONDO", f"{c.type} {pair}; retirados={removed}; protegidos={list(set(pair)&protected)}")

    def rutas_hospital(self, edge, retorno=False):
        routes=[]
        for h in self.hospitales:
            src,dst=(edge,h.edge) if retorno else (h.edge,edge)
            try:
                r=traci.simulation.findRoute(src,dst,vType="ambulance",depart=self.t,
                                             routingMode=traci.constants.ROUTING_MODE_AGGREGATED)
            except traci.TraCIException:
                continue
            if r.edges and math.isfinite(r.travelTime) and r.travelTime >= 0:
                routes.append((r.travelTime,h.id,h,r))
        return sorted(routes,key=lambda item:(item[0],item[1]))

    def despachar(self, a):
        for rank,(_,_,h,r) in enumerate(self.rutas_hospital(a.edge),1):
            decision = dict(t=self.t,accidente=a.id,hospital=h.id,rango=rank,
                            eta_s=r.travelTime,stock=len(h.cola),resultado="")
            if not h.cola:
                h.sin_stock += 1
                decision["resultado"]="sin_stock"
            elif self.disponibilidad.random()<self.args.p_sin:
                h.rechazos += 1
                decision["resultado"]="negativa_aleatoria"
            else:
                decision["resultado"]="despacho"
            self.decisions.append(decision)
            self.log("CANDIDATO", f"{a.id} {h.id} rango={rank} ETA={r.travelTime:.1f} stock={len(h.cola)} {decision['resultado']}")
            if decision["resultado"] != "despacho":
                continue
            unit=h.cola[0]
            veh=f"amb_{unit}_{a.id}"
            traci.route.add("ida_"+a.id,r.edges)
            # El origen se representa por la posición proyectada del hospital.
            traci.vehicle.add(veh,"ida_"+a.id,typeID="ambulance",departPos=str(h.pos),
                              departLane="best",arrivalPos="max")
            h.cola.popleft()
            h.despachos+=1
            a.hospital_origen,a.unidad,a.vehiculo=h.id,unit,veh
            a.estado,a.t_despacho,a.eta_s,a.ruta_m="en_camino",self.t,r.travelTime,r.length
            a.rango_hospital=rank
            self.log("DESPACHO",f"{a.id} <- {h.id} {unit} | espera {self.t-a.t_accidente:.0f} s | {len(r.edges)} aristas, {r.length:.0f} m, ETA {r.travelTime:.0f} s")
            return
        a.proximo_intento=self.t+30
        self.log("SIN_AMBULANCIA",f"{a.id} queda en cola; reintento a {a.proximo_intento:.0f}")

    def llegada(self,a,ids,arrived):
        v=a.vehiculo
        reason=""
        if v in arrived:
            reason="fin_ruta"
        elif v in ids:
            e=traci.vehicle.getRoadID(v)
            if not e or e.startswith(":"):
                return
            pos=traci.vehicle.getLanePosition(v)
            d=traci.simulation.getDistanceRoad(e,pos,a.edge,a.pos,isDriving=True)
            xy=traci.vehicle.getPosition(v)
            euclid=math.hypot(xy[0]-a.x,xy[1]-a.y)
            waiting=traci.vehicle.getWaitingTime(v)
            if 0 <= d <= 50:
                reason="carretera_50m"
            elif e == a.edge and pos <= a.pos and waiting >= 1:
                reason="cola_misma_arista"
            elif waiting >= 30 and euclid <= 300:
                reason="a_pie_300m"
            if not reason and int(self.t-a.t_despacho)%60==0 and (d>300 or d<0):
                traci.vehicle.rerouteTraveltime(v)
        if reason:
            a.estado,a.t_llegada,a.criterio_llegada="atendiendo",self.t,reason
            if v in ids:
                self.parar(v)
            self.log("LLEGADA",f"{a.id} {v} | desplazamiento {self.t-a.t_despacho:.0f} s | desde accidente {self.t-a.t_accidente:.0f} s | {reason}")

    def retornar(self,a,ids):
        v=a.vehiculo
        if self.t<a.proximo_intento:
            return
        if v in ids and traci.vehicle.getRoadID(v).startswith(":"):
            return
        routes=self.rutas_hospital(a.edge,retorno=True)
        if self.args.retorno=="origen":
            routes=[r for r in routes if r[1]==a.hospital_origen]
        if not routes:
            self.log("SIN_RUTA_RETORNO",a.id)
            a.proximo_intento=self.t+30
            return
        _,_,h,r=routes[0]
        if v in ids:
            restaurar(v)
            traci.vehicle.changeTarget(v,h.edge)
            # arrivalPos=max representa la llegada al extremo de la arista
            # hospitalaria y sigue siendo válido tras changeTarget (SUMO 1.12).
        else:
            traci.route.add("retorno_"+a.id,r.edges)
            a.vehiculo=v+"_ret"
            traci.vehicle.add(a.vehiculo,"retorno_"+a.id,typeID="ambulance",
                              departPos=str(a.pos),departLane="best",arrivalPos="max")
        for other in [a.bus,a.moto]:
            if other in ids:
                traci.vehicle.remove(other,reason=traci.constants.REMOVE_VAPORIZED)
                ids.discard(other)
        traci.poi.remove(a.id)
        a.estado,a.t_retorno,a.hospital_retorno="retorno",self.t,h.id
        self.log("RETORNO",f"{a.id} {a.vehiculo} -> {h.id}"+(" (distinto al de origen)" if h.id!=a.hospital_origen else ""))

    def cerrar(self,a):
        h=self.by_id[a.hospital_retorno]
        h.cola.append(a.unidad)
        h.recibidas+=1
        origin=self.by_id[a.hospital_origen]
        origin.ocupado_s+=self.t-a.t_despacho
        origin.ocupado_3h_s+=max(0,min(self.t,10800)-a.t_despacho)
        a.estado,a.t_disponible="cerrado",self.t
        self.log("DISPONIBLE",f"{a.unidad} en {h.id} | {a.id} misión {self.t-a.t_despacho:.0f} s | stock={len(h.cola)}")

    def verificar_flota(self):
        idle=[u for h in self.hospitales for u in h.cola]
        busy=[a.unidad for a in self.accs if a.unidad and a.estado!="cerrado"]
        assert len(idle)+len(busy)==self.fleet, "Pérdida o creación de ambulancias"
        assert len(set(idle+busy))==self.fleet, "Unidad duplicada"

    def ejecutar(self):
        try:
            self.iniciar()
            while self.t < self.args.end:
                traci.simulationStep()
                self.t=traci.simulation.getTime()
                ids=set(traci.vehicle.getIDList())
                arrived=set(traci.simulation.getArrivedIDList())
                self.teleports+=traci.simulation.getStartingTeleportNumber()
                for v,t in list(self.stopping.items()):
                    if self.t>=t:
                        if v in ids:
                            traci.vehicle.setSpeedMode(v,31)
                            traci.vehicle.setSpeed(v,0)
                        self.stopping.pop(v)
                for moto,p in list(self.pending.items()):
                    if moto in ids and not p["armed"]:
                        traci.vehicle.setSpeedMode(moto,0)
                        traci.vehicle.setLaneChangeMode(moto,0)
                        traci.vehicle.setSpeed(moto,22)
                        p["armed"]=True
                self.detectar_colisiones(ids)
                for moto,p in list(self.pending.items()):
                    left_edge = moto in ids and p["armed"] and traci.vehicle.getRoadID(moto)!=p["edge"]
                    bus_left = p["armed"] and p["bus"] in ids and traci.vehicle.getRoadID(p["bus"])!=p["edge"]
                    if self.t-p["t"]>=90 or (p["armed"] and moto not in ids) or left_edge or bus_left:
                        self.reprogramar(moto,"intento expirado, vehículo ausente o pareja salió de la arista",ids)
                if self.t<10800:
                    while self.queue and self.queue[0][0]<=self.t:
                        _,plan=heapq.heappop(self.queue)
                        self.programar_accidente(plan,ids)
                for a in self.accs:
                    if a.estado=="espera" and self.t>=a.proximo_intento:
                        self.despachar(a)
                    elif a.estado=="en_camino":
                        self.llegada(a,ids,arrived)
                    elif a.estado=="atendiendo" and self.t-a.t_llegada>=120:
                        self.retornar(a,ids)
                    elif a.estado=="retorno" and a.vehiculo in arrived:
                        self.cerrar(a)
                self.verificar_flota()
                if int(self.t)%60==0:
                    self.stocks.extend(dict(t=self.t,hospital=h.id,disponibles=len(h.cola)) for h in self.hospitales)
                if int(self.t)%1800==0:
                    print(f"t={self.t:.0f}: accidentes={len(self.accs)}, cerrados={sum(a.estado=='cerrado' for a in self.accs)}, activos={len(ids)}",flush=True)
            self.running_final=traci.vehicle.getIDCount()
            self.expected_final=traci.simulation.getMinExpectedNumber()
            guardar_csv(self.out/"remanentes.csv",[dict(id=v,tipo=traci.vehicle.getTypeID(v),
                arista=traci.vehicle.getRoadID(v),espera_s=traci.vehicle.getWaitingTime(v),
                velocidad=traci.vehicle.getSpeed(v)) for v in traci.vehicle.getIDList()],
                ["id","tipo","arista","espera_s","velocidad"])
        finally:
            if traci.isLoaded():
                traci.close()
            if hasattr(self,"console"):
                self.console.close()
            self.logfile.close()
            self.events.close()
        self.exportar()

    def exportar(self):
        rows=[]
        for a in self.accs:
            d=asdict(a)
            d.pop("proximo_intento")
            d.update(espera_s=a.t_despacho-a.t_accidente if a.t_despacho>=0 else "",
                     desplazamiento_s=a.t_llegada-a.t_despacho if a.t_llegada>=0 else "",
                     respuesta_total_s=a.t_llegada-a.t_accidente if a.t_llegada>=0 else "",
                     mision_s=a.t_disponible-a.t_despacho if a.t_disponible>=0 else "")
            rows.append(d)
        guardar_csv(self.out/"accidentes.csv",rows,list(asdict(Accidente("",0,"","","",0,0,0,"")))[:-1]+["espera_s","desplazamiento_s","respuesta_total_s","mision_s"])
        hr=[]
        for h in self.hospitales:
            # Incluye ocupación de misiones abiertas hasta el corte (censura).
            open_acc=[a for a in self.accs if a.hospital_origen==h.id and a.estado!="cerrado"]
            ocupado=h.ocupado_s+sum(self.t-a.t_despacho for a in open_acc)
            ocupado_3h=h.ocupado_3h_s+sum(max(0,min(self.t,10800)-a.t_despacho) for a in open_acc)
            hr.append(dict(hospital=h.id,tipo=h.tipo,stock_inicial=h.stock_ini,stock_final=len(h.cola),
                           despachos=h.despachos,recibidas=h.recibidas,rechazos=h.rechazos,sin_stock=h.sin_stock,
                           ocupado_s=ocupado,ocupado_3h_s=ocupado_3h,
                           utilizacion_ref_pct=100*ocupado/(10800*h.stock_ini) if h.stock_ini else "",
                           utilizacion_3h_pct=100*ocupado_3h/(10800*h.stock_ini) if h.stock_ini else ""))
        guardar_csv(self.out/"hospitales.csv",hr)
        guardar_csv(self.out/"decisiones.csv",self.decisions,["t","accidente","hospital","rango","eta_s","stock","resultado"])
        guardar_csv(self.out/"stock_tiempo.csv",self.stocks,["t","hospital","disponibles"])
        guardar_json(self.out/"ejecucion.json",dict(teleports=self.teleports,
            accidentes=len(self.accs),cerrados=sum(a.estado=="cerrado" for a in self.accs),
            intentos=self.attempts,planes_pendientes=len(self.queue)+len(self.pending),
            vehiculos_fondo_retirados=len(self.removed_background),
            running_final=self.running_final,expected_final=self.expected_final,
            wall_seconds=time.monotonic()-self.started))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--tasa",type=int,default=5)
    p.add_argument("--p-sin",type=float,default=.25)
    p.add_argument("--retorno",choices=["cercano","origen"],default="cercano")
    p.add_argument("--end",type=int,default=12600)
    p.add_argument("--output",type=Path,default=ROOT/"salida/principal")
    p.add_argument("--hospitales",type=Path,default=ROOT/"datos/hospitales.csv")
    p.add_argument("--gui",action="store_true")
    p.add_argument("--gui-iniciar",action="store_true",help="Iniciar SUMO-GUI sin pulsar Play")
    args=p.parse_args()
    if not 0 <= args.p_sin <= 1 or args.tasa<0 or args.end<=0:
        p.error("p-sin debe estar en [0,1], tasa >= 0 y end > 0")
    Simulacion(args).ejecutar()


if __name__=="__main__":
    main()
