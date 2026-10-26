#!/usr/bin/env python3
"""Informe y resultados derivados de CSV, XML, auditoría y capturas actuales."""
import json
from html import escape
from pathlib import Path
import pandas as pd
from entorno import ROOT


def num(v):
    return "N/A" if v is None or pd.isna(v) else f"{v:,.1f}".replace(",","_").replace(".",",").replace("_",".")


def load(path):
    return json.loads((ROOT/path).read_text())


def mdtable(df):
    lines=["| "+" | ".join(map(str,df.columns))+" |","| "+" | ".join(["---"]*len(df.columns))+" |"]
    lines.extend("| "+" | ".join(map(str,row))+" |" for row in df.itertuples(index=False,name=None))
    return "\n".join(lines)


def main():
    b=load("salida/base/resumen.json");s=load("salida/principal/resumen.json")
    date=load("salida/principal/parametros.json")["fecha_utc"][:10]
    a=pd.read_csv(ROOT/"salida/principal/accidentes.csv")
    h=pd.read_csv(ROOT/"salida/principal/hospitales.csv")
    located=pd.read_csv(ROOT/"salida/principal/hospitales_ubicados.csv").fillna("")
    net=pd.read_csv(ROOT/"salida/preparacion/redes.csv")
    av=pd.read_csv(ROOT/"salida/tablas/avenidas.csv")
    comp=pd.read_csv(ROOT/"salida/tablas/comparacion_escenarios.csv")
    audit=load("salida/validacion_global.json");replay=load("salida/reproducibilidad.json")
    gui_ok=any(c["prueba"]=="GUI: evidencia vigente de hospitales, cola y retorno" and c["ok"] for r in audit for c in r["pruebas"])
    errors=sum(r["errores"] for r in audit);warnings=sum(r["advertencias"] for r in audit)
    checks=sum(len(r["pruebas"]) for r in audit);repeated=sum(r["identico"] for r in replay)
    pairs=comp[comp.tasa==5].pivot(index="semilla",columns="politica",values=["mediana_s","p90_s"])
    comparison=pd.DataFrame([[seed,*[num(row[(metric,policy)]) for metric in ["mediana_s","p90_s"] for policy in ["cercano","origen"]]]
        for seed,row in pairs.iterrows()],columns=["Semilla","Mediana cercano [s]","Mediana origen [s]","P90 cercano [s]","P90 origen [s]"])
    delta=pairs["mediana_s"]["origen"]-pairs["mediana_s"]["cercano"]
    means=comp[comp.tasa==5].groupby("politica").mediana_s.mean()
    bad=located[located.distancia_m>=150]
    spatial=("A3 pendiente: "+"; ".join(f"{r.id}: {r.distancia_m:.2f} m" for r in bad.itertuples())+
        ". El límite es estrictamente menor de 150 m. Hace falta verificar el acceso o recibir la coordenada del capítulo. "
        "No se desplazaron puntos para aparentar cumplimiento.") if len(bad) else "Los siete hospitales cumplen distancia menor de 150 m."
    scope=("La red original del ZIP docente produce 1.745 aristas y 176 semáforos con los filtros del taller. "
        "El ZIP incluye únicamente cuenca_net.xml. Los puntos hospitalarios siguen procediendo de OSM y los tipos de vehículo "
        "son los implementados en este proyecto. SUMO 1.12.0. "+spatial)
    result=(f"Semilla 42: {s['accidentes']} accidentes, {s['cerrados']} misiones cerradas y {s['censurados']} censuradas; "
        f"{s['teleports']} teleports. Respuesta: media {num(s['respuesta_total']['media'])} s, mediana {num(s['respuesta_total']['mediana'])} s, "
        f"p90 {num(s['respuesta_total']['p90'])} s y máximo {num(s['respuesta_total']['maximo'])} s. "
        f"Espera media {num(s['espera']['media'])} s; mediana de misión {num(s['mision']['mediana'])} s. "
        f"Flota inicial {s['flota']}, disponible final {int(h.stock_final.sum())}; "
        f"activos al corte {s['running_final']}, esperados {s['expected_final']}.")
    stock="Stock inicial → final: "+"; ".join(f"{r.hospital}: {r.stock_inicial} → {r.stock_final}" for r in h.itertuples())+"."
    public=h[h.tipo=="publico"].sort_values("utilizacion_ref_pct",ascending=False).iloc[0]
    usage=("Utilización = ocupación atribuida al origen / (10.800 s × stock inicial). Con flota móvil es un índice de carga; "
        f"si el stock inicial es cero se informa N/A. Mayor índice público: {public.hospital}, {num(public.utilizacion_ref_pct)}%.")
    chosen=a[a.rango_hospital>1].sort_values("rango_hospital",ascending=False).iloc[0]
    dispatch=("Se ordena por tiempo de ruta agregado y se revisan stock y negativa p=0,25. "
        f"Ejemplo: {chosen.id} salió de {chosen.hospital_origen}, rango {int(chosen.rango_hospital)}. "
        "decisiones.csv registra la ETA y el motivo de cada descarte previo.")
    stress=comp[comp.tasa==15].iloc[0];sa=pd.read_csv(ROOT/"salida"/stress.escenario/"accidentes.csv")
    stress_note=(f"Con 15/h: {int(stress.accidentes)} accidentes, {int(stress.cerrados)} cerrados y {int(stress.censurados)} censurados; "
        f"{int((sa.plan_id>0).sum())} de agenda y {int((sa.plan_id==0).sum())} naturales. "
        f"Mediana {num(s['respuesta_total']['mediana'])} → {num(stress.mediana_s)} s; "
        f"p90 {num(s['respuesta_total']['p90'])} → {num(stress.p90_s)} s; espera media {num(stress.espera_media_s)} s. "
        "No se forzó la saturación del ejemplo docente.")
    residual=[]
    for r in comp.itertuples():
        e=load(f"salida/{r.escenario}/ejecucion.json")
        if e["running_final"] or e["expected_final"]:residual.append(f"{r.escenario}: {e['running_final']} activos, {e['expected_final']} esperados")
    drain="Vaciado: "+("; ".join(residual) if residual else "todas las corridas comparadas terminan sin tráfico pendiente.")
    failure=("La semilla 7/origen abortó a 7.815 s por una aserción interna de MSVehicle::getBackPositionOnLane, SUMO 1.12.0. "
        "Se excluyen sus salidas incompletas. Se eligió la semilla 8 para ambas políticas antes de ver sus resultados. "
        "Log y parámetros: salida/fallos/origen_s7_t5/. Cercano/7 queda como diagnóstico local fuera de la comparación pareada.")
    rubric=pd.DataFrame([
        ["A1","Verificado",f"ZIP docente; {int(net.iloc[1].aristas)} aristas, {int(net.iloc[1].semaforos)} TLS; join-dist=25"],
        ["A2","Verificado",f"{b['vehicles']['inserted']} insertados, tres tipos, {b['teleports']['total']} teleports; macro cada 900 s"],
        ["A3","Parcial" if len(bad) else "Verificado",f"7 hospitales; 49 rutas; distancia máxima {num(located.distancia_m.max())} m"],
        ["A4","Verificado",f"Flota {s['flota']}; bases con cero; repetición {repeated}/{len(replay)} archivos"],
        ["B1","Verificado",f"{len(a)} choques físicos en {a.edge.nunique()} aristas distintas"],
        ["B2","Verificado",f"Ranking ETA; {s['rechazos']} negativas aleatorias documentadas"],
        ["B3","Verificado",f"{s['cerrados']} retornos; flota conservada; restauración 31/1621/−1"],
        ["B4","Verificado","CSV, estadísticos y siete figuras PNG/SVG/PDF"],
        ["GUI","Comprobada" if gui_ok else "Pendiente","Presentación ante docente a cargo del estudiante"],
        ["Extensión","Ejecutada",f"{len(pairs)} semillas × 2 políticas; 15/h; fallo de semilla 7 documentado"]],columns=["Criterio","Estado técnico","Evidencia"])
    validation=(f"{checks} controles: {errors} errores de invariantes y {warnings} advertencias. "
        f"Repetición: {repeated}/{len(replay)} archivos idénticos por SHA-256. Cero errores de invariantes no equivale "
        "a cumplimiento total: revisar A3. Las advertencias incluyen distancia, prueba negativa y casos de otras semillas.")
    sections=[]
    def add(title,texts=(),table=None,figure=None,height=310,code=None):
        sections.append(dict(title=title,texts=list(texts),table=table,figure=figure,height=height,code=code))
    nt=net[["red","aristas","nodos","semaforos","km_arista","componentes_debiles"]].round(2)
    add("01 · Escenario y procedencia",[scope,"ZIP y red conservan SHA-256. Un netconvert aplica jerarquía vial, "
        "bbox, mayor componente, simplificación y junctions.join-dist=25. km_arista suma vías dirigidas, no calles únicas."],nt)
    loc=located[["id","calle","distancia_convertRoad_m","distancia_m","stock_ini"]].copy()
    loc.columns=["Hospital","Vía asignada","Proyección [m]","Acceso útil [m]","Stock inicial"]
    for c in loc.columns[2:4]:loc[c]=loc[c].map(num)
    add("02 · Control de acceso hospitalario",["convertRoad con clase emergency, seguido de rutas de ida y vuelta. "
        "Los 49 pares se comprueban. Se conservan las proyecciones originales y las correcciones de conectividad.",spatial],loc)
    add("03 · Hospitales y accidentes",[f"{len(a)} accidentes en {a.edge.nunique()} aristas. Red del ZIP docente; hospitales OSM; accidentes TraCI. "
        "Cartografía: © OpenStreetMap contributors."],figure="salida/figuras/01_mapa.png",height=390)
    add("04 · Línea base y tráfico",[f"{b['vehicles']['inserted']} vehículos insertados; {b['teleports']['total']} teleports; "
        f"{b['safety']['collisions']} colisiones de fondo; {b['vehicles']['running']} activos al corte. Duración media {b['vehicleTripStatistics']['duration']} s. "
        "Demanda: 1.200 autos/h, 100 buses/h, 300 motos/h. Ventanas de 900 s; demanda hasta 180 min, vaciado hasta 210 min."],
        figure="salida/figuras/02_trafico_macro.png",height=345)
    avout=av[["avenida","q","k","v","kv","error_q_vs_kv_pct"]].round(2)
    avout.columns=["Avenida","q [veh/h]","k [veh/km]","v [km/h]","Media k·v [veh/h]","Error [%]"]
    add("05 · Diagrama fundamental y avenidas",["q cuenta entradas; k·v combina presencia y velocidad. No se iguala el producto de medias "
        "con pesos diferentes a la media del producto. Promedios bajos no descartan colas locales ni calibran capacidad."],avout,
        "salida/figuras/03_diagrama_fundamental.png",250)
    add("06 · Controlador y prueba de seguridad",["Identidades persistentes y colas FIFO; flota verificada cada segundo. "
        "El bit 0 controla velocidad segura. En la recta, modos 30 y 0 chocan; 31 y 23 no. Pedir 22 m/s no anula v_safe con modo 31.",
        "Retorno: setSpeedMode(31), setLaneChangeMode(1621), setSpeed(-1). Modo 0 conserva interpretación heredada; no desactiva todos los bits modernos."],
        pd.read_csv(ROOT/"salida/modos/resultados.csv"),code="espera -> en_camino -> atendiendo (120 s) -> retorno -> cerrado\nreintento 30 s       tres criterios de llegada        vuelve a la cola")
    add("07 · Respuesta por accidente",[result,"Respuesta total = espera + desplazamiento. P90 interpolado linealmente. "
        "Estadísticos de misiones cerradas; son mediciones de una simulación."],figure="salida/figuras/04_respuesta.png",height=305)
    add("08 · Uso hospitalario",[stock,usage],figure="salida/figuras/05_hospitales.png",height=325)
    add("09 · Migración y disponibilidad",[f"Migración: {num(s['migracion_pct'])}% de misiones cerradas. Una base que empieza en cero "
        "puede despachar después de recibir unidades. Se incorpora la unidad a la cola destino solo al observar su llegada."],
        figure="salida/figuras/06_migracion.png",height=355)
    add("10 · Comparación de políticas",[f"Media de medianas: cercano {num(means['cercano'])} s; origen {num(means['origen'])} s. "
        f"Diferencia origen − cercano: media {num(delta.mean())} s, desviación muestral {num(delta.std(ddof=1))} s. "
        f"Cercano tiene menor mediana en {int((delta>0).sum())}/{len(delta)} pares. Cinco pares no prueban superioridad universal.",drain,failure],comparison)
    add("11 · Variación y aumento de carga",[stress_note,"Demanda fija y semillas comunes. Las decisiones cambian el tráfico y los lugares "
        "de choque; los incidentes individuales no son pares idénticos."],figure="salida/figuras/07_extension.png",height=315)
    add("12 · Validaciones A/B",[validation,"Cinco tests: corrida válida, inventario corrupto, tiempo alterado, choque sin soporte XML y negativa total. "
        "p_sin=1 acaba a 1.200 s con espera deliberada y reintentos cada 30 s; se excluye de las políticas."],rubric)
    if gui_ok:
        caps=load("salida/visual/verificacion_visual.json")["capturas"]
        for key,label in [("01_hospitales","Hospitales"),("02_accidente_cola","Choque y cola"),("03_retorno","Retorno y disponibilidad")]:
            cap=caps[key]
            detail=f"Estado observado a t={cap['t_s']:.0f} s. "
            if key=="01_hospitales":detail+="Siete POI y flota inicial con privados en cero."
            elif key=="02_accidente_cola":detail+=f"{cap['accidente']}; bus/moto a 0 m/s; tráfico detenido detrás: {', '.join(cap['cola'])}."
            else:detail+=f"{cap['unidad']}: {cap['origen']} → {cap['destino']}; stock receptor {cap['stock_antes']} → {cap['stock_despues']}. La unidad ya está en cola."
            add("Evidencia SUMO-GUI · "+label,[detail,"Captura del simulador; corroboración TraCI en verificacion_visual.json y eventos.log. "
                "La exposición y evaluación ante el docente corresponden al estudiante."],figure=cap["archivo"],height=350)
    add("Discusión técnica",[dispatch,"Llegadas observadas: "+", ".join(f"{k}: {v}" for k,v in a.criterio_llegada.value_counts().items())+
        ". La llegada a pie tras 30 s detenido a ≤300 m es una aproximación sin peatón ni tiempo de caminata explícitos.",
        f"No usar teleport conserva bloqueos. warn conserva accidentados. Se retiraron {s['vehiculos_fondo_retirados']} vehículos "
        "por otras colisiones; esta intervención se documenta y no se confunde con teletransporte.",spatial])
    add("Reproducir, demostrar y entregar",["Desde RetoAmbulancia, con Docker y van3twin:jammy. COMANDOS.md explica cada paso. "
        "Fuentes y supuestos: METODOLOGIA.md; columnas: DATOS.md. Entrega: sección Talleres, miércoles 28 de octubre de 2026, 20:00 (hora local del usuario). "
        "Repositorio del autor: https://github.com/angelrampolo/practica04-ambulancias-cuenca. "
        "El estado de publicación y de carga en la plataforma se registra en ENTREGA.md."],code=
        "python3 -m venv .venv\n.venv/bin/python -m pip install -r requirements.txt\nmake reproducir PYTHON=.venv/bin/python\n\n"
        "# Demostracion: visor VNC en localhost:5902\n./scripts/demo_gui.sh\n# Capturas automaticas y reporte\nmake gui-validar\nmake validar informe PYTHON=.venv/bin/python\n\n"
        "python3 scripts/comprobar_repeticion.py\npython3 -m unittest discover -s pruebas -v\npython3 scripts/empaquetar.py\nsha256sum -c MANIFEST.sha256")
    md=["# Resultados y validación del reto\n",f"Ejecución principal: {date} (UTC).\n", "Angel Ramiro Apolo Aguilar · Universidad de Cuenca · Ingeniería en Telecomunicaciones · 10.º ciclo · Redes Vehiculares y Heterogéneas · angel.apolo@ucuenca.edu.ec",result]
    for sec in sections:
        md.append("\n## "+sec["title"]+"\n");md.extend(sec["texts"])
        if sec["table"] is not None:md.append(mdtable(sec["table"]))
        if sec["figure"]:md.append(f"![{sec['title']}](../{sec['figure']})")
        if sec["code"]:md.append("```bash\n"+sec["code"]+"\n```")
    (ROOT/"docs/RESULTADOS.md").write_text("\n\n".join(md)+"\n")
    from informe_ieee import generar
    generar()
    print("Generados RESULTADOS.md, fuentes LaTeX y PDF IEEE")


if __name__=="__main__":main()
