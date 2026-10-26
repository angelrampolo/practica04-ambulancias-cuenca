#!/usr/bin/env python3
"""Genera tablas y macros verificables y compila el artículo IEEE con Tectonic."""
import json
import os
import shutil
import subprocess
from pathlib import Path
import pandas as pd
from entorno import ROOT, guardar_json, sha256

TEX=ROOT/"docs/latex"
NAMES={"VCM":"Vicente Corral","IESS":"IESS","MILITAR":"Militar","MUNI_PATAMARCA":"M. Patamarca",
       "MUNI_VALLE":"M. El Valle","MONTE_SINAI":"Monte Sinaí","DEL_RIO":"Del Río"}


def esc(value):
    mapping={"\\":r"\textbackslash{}","_":r"\_","&":r"\&","%":r"\%","#":r"\#","$":r"\$","{":r"\{","}":r"\}","º":r"\textordmasculine{}"}
    return "".join(mapping.get(c,c) for c in str(value))


def n(value,dec=1):
    return "N/A" if pd.isna(value) else f"{value:.{dec}f}".replace(".",",")


def load(path):
    return json.loads((ROOT/path).read_text())


def tabla(name,columns,rows,spec):
    lines=[r"\begin{tabular}{"+spec+"}",r"\toprule"," & ".join(columns)+r" \\",r"\midrule"]
    lines.extend(" & ".join(esc(v) for v in row)+r" \\" for row in rows)
    lines.extend([r"\bottomrule",r"\end{tabular}"])
    (TEX/(name+".tex")).write_text("\n".join(lines)+"\n")


def generar():
    TEX.mkdir(parents=True,exist_ok=True)
    s=load("salida/principal/resumen.json");b=load("salida/base/resumen.json");author=load("docs/autor.json")
    a=pd.read_csv(ROOT/"salida/principal/accidentes.csv");h=pd.read_csv(ROOT/"salida/principal/hospitales.csv")
    loc=pd.read_csv(ROOT/"salida/principal/hospitales_ubicados.csv")
    net=pd.read_csv(ROOT/"salida/preparacion/redes.csv");av=pd.read_csv(ROOT/"salida/tablas/avenidas.csv")
    c=pd.read_csv(ROOT/"salida/tablas/comparacion_escenarios.csv")
    audit=load("salida/validacion_global.json");replay=load("salida/reproducibilidad.json")
    visual=load("salida/visual/verificacion_visual.json")["capturas"]
    assert any(p["prueba"]=="GUI: evidencia vigente de hospitales, cola y retorno" and p["ok"] for r in audit for p in r["pruebas"]),"Actualizar demo y auditoría antes del informe"
    assert not any(r["errores"] for r in audit),"Resolver errores de auditoría antes del informe"
    stress=c[c.tasa==15].iloc[0]
    means=c[c.tasa==5].groupby("politica").mediana_s.mean()
    paired=c[c.tasa==5].pivot(index="semilla",columns="politica",values="mediana_s")
    diff=paired.origen-paired.cercano
    chosen=a[a.rango_hospital>1].sort_values("rango_hospital",ascending=False).iloc[0]
    publico=h[h.tipo=="publico"].sort_values("utilizacion_ref_pct",ascending=False).iloc[0]
    retorno=visual["03_retorno"]
    values=dict(Autor=author["nombre"],Correo=author["correo"],Universidad=author["universidad"],Carrera=author["carrera"],
        Asignatura=author["asignatura"],Ciclo=author["ciclo"],Accidentes=len(a),Cerrados=s["cerrados"],
        Mediana=n(s["respuesta_total"]["mediana"]),Pnoventa=n(s["respuesta_total"]["p90"]),Media=n(s["respuesta_total"]["media"]),
        Maximo=n(s["respuesta_total"]["maximo"]),MedianaMision=n(s["mision"]["mediana"]),Migracion=n(s["migracion_pct"]),
        Flota=s["flota"],PatamarcaFinal=int(h[h.hospital=="MUNI_PATAMARCA"].iloc[0].stock_final),
        MonteFinal=int(h[h.hospital=="MONTE_SINAI"].iloc[0].stock_final),
        Demanda=b["vehicles"]["inserted"],ColisionesBase=b["safety"]["collisions"],DuracionBase=b["vehicleTripStatistics"]["duration"].replace(".",","),
        GeoMax=n(loc.distancia_m.max(),2),Controles=sum(len(r["pruebas"]) for r in audit),Advertencias=sum(r["advertencias"] for r in audit),
        Repetidos=sum(r["identico"] for r in replay),FondoRetirado=s["vehiculos_fondo_retirados"],Negativas=s["rechazos"],
        Planeados=int((a.plan_id>0).sum()),Naturales=int((a.plan_id==0).sum()),
        EstresAcc=int(stress.accidentes),EstresCerr=int(stress.cerrados),EstresMed=n(stress.mediana_s),EstresP=n(stress.p90_s),
        MediaCercano=n(means["cercano"]),MediaOrigen=n(means["origen"]),Diferencia=n(diff.mean()),Desviacion=n(diff.std(ddof=1)),
        ParesGana=int((diff>0).sum()),EjemploAcc=chosen.id,EjemploHospital=NAMES[chosen.hospital_origen],EjemploRango=int(chosen.rango_hospital),
        UsoHospital=NAMES[publico.hospital],UsoPublico=n(publico.utilizacion_ref_pct),
        GuiAcc=visual["02_accidente_cola"]["accidente"],GuiTiempo=n(visual["02_accidente_cola"]["t_s"],0),
        GuiUnidad=retorno["unidad"],GuiOrigen=NAMES[retorno["origen"]],GuiDestino=NAMES[retorno["destino"]],
        GuiAntes=retorno["stock_antes"],GuiDespues=retorno["stock_despues"],GuiRetorno=n(retorno["t_s"],0))
    (TEX/"datos.tex").write_text("% Generado desde CSV/JSON: no editar a mano.\n"+"\n".join(r"\newcommand{"+chr(92)+key+"}{"+esc(value)+"}" for key,value in values.items())+"\n")
    tabla("tabla_red",["Red","Aristas","Semáforos","km dirigidos"],[["Completa" if i==0 else "Recortada",int(r.aristas),int(r.semaforos),n(r.km_arista)] for i,r in net.iterrows()],"lrrr")
    tabla("tabla_hospitales",["Hospital","Dist. [m]","Inicial","Final","Despachos","Recibidas","Uso [\\%]"],
        [[NAMES[r.hospital],n(loc[loc.id==r.hospital].iloc[0].distancia_m,2),r.stock_inicial,r.stock_final,r.despachos,r.recibidas,n(r.utilizacion_ref_pct)] for r in h.itertuples()],"lrrrrrr")
    tabla("tabla_avenidas",["Avenida",r"$q$ [veh/h]",r"$k$ [veh/km]",r"$v$ [km/h]",r"$\overline{kv}$ [veh/h]","Error [\\%]"],
        [[r.avenida,n(r.q,2),n(r.k,2),n(r.v,2),n(r.kv,2),n(r.error_q_vs_kv_pct,2)] for r in av.itertuples()],"lrrrrr")
    rows=[]
    for seed in sorted(c[c.tasa==5].semilla.unique()):
        q=c[(c.tasa==5)&(c.semilla==seed)].set_index("politica")
        rows.append([seed,*[n(q.loc[p,m]) for m in ["mediana_s","p90_s"] for p in ["cercano","origen"]]])
    tabla("tabla_politicas",["Semilla",r"\shortstack{Mediana\\cercano [s]}",r"\shortstack{Mediana\\origen [s]}",r"\shortstack{P90\\cercano [s]}",r"\shortstack{P90\\origen [s]}"],rows,"rrrrr")
    decision=pd.read_csv(ROOT/"salida/principal/decisiones.csv")
    decision=decision[(decision.accidente==chosen.id)&(decision.t==chosen.t_despacho)]
    reasons={"sin_stock":"Sin unidades","negativa_aleatoria":"Negativa","despacho":"Despacho"}
    tabla("tabla_despacho",["Rango","Hospital","ETA [s]","Stock","Decisión"],
        [[r.rango,NAMES[r.hospital],n(r.eta_s),r.stock,reasons[r.resultado]] for r in decision.itertuples()],"rlrrl")
    modes=pd.read_csv(ROOT/"salida/modos/resultados.csv")
    tabla("tabla_modos",["Modo","Colisión"],[[r.speedMode,"Sí" if r.colision else "No"] for r in modes.itertuples()],"rc")
    byhour=a.groupby((a.t_accidente//3600).astype(int)).size().reindex([0,1,2],fill_value=0)
    tabla("tabla_horas",["Hora","Accidentes"],[[i+1,int(count)] for i,count in enumerate(byhour)],"cr")
    bibliography=ROOT/"docs/latex/Informe_Reto_Ambulancias.tex"
    build=TEX/"build";build.mkdir(exist_ok=True)
    compiler=shutil.which("tectonic")
    if not compiler:raise SystemExit("Instala Tectonic o compila docs/latex/Informe_Reto_Ambulancias.tex con pdfLaTeX (dos pasadas).")
    env=os.environ.copy();env.setdefault("XDG_CACHE_HOME","/tmp/reto-tex-cache")
    command=[compiler,"--untrusted","--keep-logs","--outdir",str(build),str(bibliography)]
    with (build/"compilacion.txt").open("w") as log:
        subprocess.run(command,cwd=TEX,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    pdf=build/"Informe_Reto_Ambulancias.pdf"
    shutil.copy2(pdf,ROOT/"docs/Informe_Reto_Ambulancias.pdf")
    guardar_json(build/"compilacion.json",dict(comando=command,formato="IEEEtran conference, A4, doble columna",
        autor=author["nombre"],fuente_sha256=sha256(bibliography),datos_sha256=sha256(TEX/"datos.tex"),pdf_sha256=sha256(pdf)))


if __name__=="__main__":generar()
