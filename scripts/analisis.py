#!/usr/bin/env python3
"""Tablas auditables y figuras vectoriales a partir de las salidas reales."""
import argparse
import json
import os
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR","/tmp/reto-ambulancia-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import pandas as pd
from entorno import ROOT, guardar_json

FIG=ROOT/"salida/figuras"
TAB=ROOT/"salida/tablas"
NAVY="#152D47"
TEAL="#008D91"
RED="#DA544F"
GOLD="#EBA747"
PALETTE=["#007F86","#4477AA","#AA3377","#228833","#CCBB44","#EE7733","#7A71A8"]
LABELS={"VCM":"Vicente Corral M.","IESS":"IESS","MILITAR":"Militar",
        "MUNI_PATAMARCA":"M. Patamarca","MUNI_VALLE":"M. El Valle",
        "MONTE_SINAI":"Monte Sinaí","DEL_RIO":"Del Río"}


def estilo():
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":12,"axes.titlesize":15,
        "axes.titleweight":"bold","axes.labelcolor":NAVY,"text.color":NAVY,
        "axes.edgecolor":"#CBD5DF","axes.spines.top":False,"axes.spines.right":False,
        "axes.grid":True,"grid.color":"#E3E9EE","grid.linewidth":.6,"axes.axisbelow":True,
        "figure.facecolor":"white","axes.facecolor":"white","savefig.facecolor":"white",
        "legend.frameon":False,"pdf.fonttype":42,"svg.fonttype":"none"})
    FIG.mkdir(parents=True,exist_ok=True)
    TAB.mkdir(parents=True,exist_ok=True)


def guardar(fig,name,note):
    fig.text(.02,.012,note,fontsize=10,color="#637487")
    fig.subplots_adjust(bottom=.15,top=.88,hspace=.45,wspace=.35)
    for suffix in ["png","svg","pdf"]:
        fig.savefig(FIG/f"{name}.{suffix}",dpi=220,bbox_inches="tight")
    plt.close(fig)


def percentiles(values):
    x=np.asarray(values,dtype=float)
    if not len(x):
        return dict(n=0,media=None,mediana=None,p90=None,maximo=None)
    return dict(n=len(x),media=float(x.mean()),mediana=float(np.median(x)),
                p90=float(np.percentile(x,90)),maximo=float(x.max()))


def resumen(folder):
    a=pd.read_csv(folder/"accidentes.csv")
    h=pd.read_csv(folder/"hospitales.csv")
    p=json.loads((folder/"parametros.json").read_text())
    e=json.loads((folder/"ejecucion.json").read_text())
    e={k:v for k,v in e.items() if k not in ["accidentes","cerrados"]}
    closed=a[a.estado=="cerrado"]
    result=dict(carpeta=folder.name,semilla=p["seed"],retorno=p["retorno"],tasa=p["tasa"],
        accidentes=len(a),cerrados=len(closed),censurados=len(a)-len(closed),
        respuesta_total=percentiles(closed.respuesta_total_s),
        desplazamiento=percentiles(closed.desplazamiento_s),
        espera=percentiles(closed.espera_s),mision=percentiles(closed.mision_s),
        migracion_pct=float(100*(closed.hospital_origen!=closed.hospital_retorno).mean()) if len(closed) else None,
        rechazos=int(h.rechazos.sum()),flota=int(h.stock_inicial.sum()),**e)
    guardar_json(folder/"resumen.json",result)
    (folder/"resumen.txt").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    return a,h,result


def red_geometria():
    root=ET.parse(ROOT/"escenario/cuenca_ciudad.net.xml").getroot()
    rows=[]
    shapes=[]
    for e in root.findall("edge"):
        if e.get("function")=="internal":
            continue
        lanes=e.findall("lane")
        if not lanes:
            continue
        lane=lanes[0]
        rows.append(dict(edge=e.get("id"),calle=e.get("name",""),
                         L=float(lane.get("length")),carriles=len(lanes)))
        shapes.append(np.array([[float(c) for c in pair.split(",")] for pair in lane.get("shape").split()])/1000)
    return pd.DataFrame(rows),shapes


def mapa(a,folder,shapes):
    h=pd.read_csv(folder/"hospitales_ubicados.csv")
    fig,ax=plt.subplots(figsize=(10.8,9))
    ax.add_collection(LineCollection(shapes,linewidths=.55,colors="#B9C7D1",alpha=.8))
    ax.scatter(a.x/1000,a.y/1000,s=55,c=GOLD,edgecolors="white",zorder=3,label="Accidente bus–moto")
    for _,r in a.iterrows():
        offsets={"ACC01":(10,5),"ACC13":(-47,13),"ACC06":(16,16),"ACC04":(30,-3),"ACC07":(30,-8),"ACC02":(16,-18)}
        ax.annotate(r.id,(r.x/1000,r.y/1000),xytext=offsets.get(r.id,(4,-10)),textcoords="offset points",fontsize=11,color="#9B681F",
                    arrowprops=dict(arrowstyle="-",lw=.6,color="#9B681F",shrinkA=3,shrinkB=5) if r.id in offsets else None)
    for i,(_,r) in enumerate(h.iterrows()):
        ax.scatter(r.x/1000,r.y/1000,marker="P",s=100,color=PALETTE[i],edgecolors="white",zorder=4)
        ax.annotate(LABELS[r.id],(r.x/1000,r.y/1000),xytext=(8,10),textcoords="offset points",
                    fontsize=11,fontweight="bold",bbox=dict(fc="white",ec="none",alpha=.88,pad=2))
    ax.autoscale()
    ax.set_aspect("equal")
    ax.set(xlabel="Coordenada local X [km]",ylabel="Coordenada local Y [km]")
    ax.set_title("Cuenca · cobertura hospitalaria y accidentes",loc="left",pad=20)
    ax.annotate("N",xy=(.96,.94),xytext=(.96,.86),xycoords="axes fraction",ha="center",fontweight="bold",
                arrowprops=dict(arrowstyle="->",color=NAVY))
    ax.legend(loc="lower left")
    guardar(fig,"01_mapa","Red docente, base © OpenStreetMap contributors (ODbL). Hospitales: OSM; accidentes: TraCI, semilla 42.")


def macro(net):
    path=ROOT/"salida/base/macro.xml"
    if not path.exists():
        return
    rows=[]
    for interval in ET.parse(path).getroot().findall("interval"):
        start,end=float(interval.get("begin")),float(interval.get("end"))
        for e in interval.findall("edge"):
            rows.append(dict(inicio_s=start,fin_s=end,edge=e.get("id"),
                q=float(e.get("entered",0))*3600/(end-start),
                k=float(e.get("density",0)),v=float(e.get("speed",0))*3.6,
                veh_s=float(e.get("sampledSeconds",0))))
    data=pd.DataFrame(rows).merge(net,on="edge",validate="many_to_one")
    data["k_carril"]=data.k/data.carriles
    data["kv"]=data.k*data.v
    def weighted(g):
        return dict(q=np.average(g.q,weights=g.L),k=np.average(g.k,weights=g.L),
            v=np.average(g.v,weights=g.q) if g.q.sum()>0 else 0,
            kv=np.average(g.kv,weights=g.L),k_carril=np.average(g.k_carril,weights=g.L))
    rows=[]
    for (start,end),g in data.groupby(["inicio_s","fin_s"]):
        rows.append(dict(inicio_min=start/60,fin_min=end/60,**weighted(g)))
    table=pd.DataFrame(rows)
    table.to_csv(TAB/"macro_intervalos.csv",index=False)
    avenue=[]
    stationary=data[(data.inicio_s>=900)&(data.fin_s<=10800)].copy()
    normalize=lambda v: "".join(c for c in unicodedata.normalize("NFD",v.lower()) if not unicodedata.combining(c))
    stationary["normalized"]=stationary.calle.map(normalize)
    for name,pattern in [("Huayna Cápac","huayna capac"),("Las Américas","las americas"),("Circunvalación Sur","circunvalacion sur")]:
        subset=stationary[stationary.normalized.str.contains(pattern,regex=False)]
        if subset.empty:
            continue
        row=dict(avenida=name,aristas=subset.edge.nunique(),**weighted(subset))
        row["error_q_vs_kv_pct"]=100*(row["q"]-row["kv"])/row["kv"] if row["kv"] else 0
        avenue.append(row)
    pd.DataFrame(avenue).to_csv(TAB/"avenidas.csv",index=False)
    fig,axes=plt.subplots(3,1,figsize=(11.5,8.7),sharex=True)
    for ax,key,label,color in zip(axes,["q","k","v"],["Flujo [veh/h]","Densidad [veh/km]","Velocidad [km/h]"],[TEAL,NAVY,GOLD]):
        ax.plot((table.inicio_min+table.fin_min)/2,table[key],"o-",color=color,lw=2,ms=5)
        ax.axvspan(0,15,color="#EEF2F5")
        ax.axvspan(180,210,color="#F9EAD5")
        ax.set_ylabel(label)
    axes[0].set_title("Tráfico de fondo · llenado, circulación y vaciado",loc="left",pad=18)
    axes[-1].set(xlabel="Tiempo de simulación [min]",xlim=(0,210))
    guardar(fig,"02_trafico_macro","Intervalos de 15 min. q y k: ponderados por longitud; v: ponderada por flujo. El sombreado final inicia a los 180 min.")
    fig,axes=plt.subplots(1,2,figsize=(12,5.3))
    sc=axes[0].scatter(table.k,table.q,c=(table.inicio_min+table.fin_min)/2,cmap="viridis",s=65,edgecolors="white")
    axes[0].plot(table.k,table.q,color="#BFCAD4",lw=1,zorder=0)
    axes[0].set(title="Red · trayectoria q–k",xlabel="Densidad [veh/km]",ylabel="Flujo [veh/h]")
    fig.colorbar(sc,ax=axes[0],label="Tiempo [min]",shrink=.8)
    for i,r in enumerate(avenue):
        axes[1].scatter(r["k"],r["q"],color=PALETTE[i],s=75,label=r["avenida"])
    axes[1].set(title="Avenidas · promedio de 15–180 min",xlabel="Densidad [veh/km]",ylabel="Flujo [veh/h]")
    axes[1].legend(loc="best",fontsize=10)
    guardar(fig,"03_diagrama_fundamental","q usa entradas de arista; k·v usa presencia y velocidad. Sus diferencias finitas se cuantifican en tablas/avenidas.csv.")


def respuesta(a,result):
    closed=a[a.estado=="cerrado"].sort_values("t_accidente")
    fig,ax=plt.subplots(figsize=(12.5,6.5))
    colors={h:c for h,c in zip(LABELS,PALETTE)}
    x=np.arange(len(closed))
    ax.bar(x,closed.desplazamiento_s,color=[colors[v] for v in closed.hospital_origen],width=.72)
    ax.bar(x,closed.espera_s,bottom=closed.desplazamiento_s,color=RED,label="Espera de despacho")
    med=result["respuesta_total"]["mediana"]
    p90=result["respuesta_total"]["p90"]
    if med is not None:
        ax.axhline(med,color=NAVY,lw=1.6,ls="--",label=f"Mediana total · {med:.1f} s".replace(".",","))
        ax.axhline(p90,color=RED,lw=1.4,ls=":",label=f"P90 total · {p90:.1f} s".replace(".",","))
    for i,(_,r) in enumerate(closed.iterrows()):
        ax.text(i,r.respuesta_total_s+8,str(int(r.respuesta_total_s)),ha="center",fontsize=10)
    ax.set_xticks(x,[f"{r.id}\n{r.t_accidente/60:.0f}" for _,r in closed.iterrows()],fontsize=10)
    ax.set(ylabel="Accidente → llegada [s]",xlabel="Accidente e instante de ocurrencia [min]")
    ax.set_title("Tiempo de respuesta total por accidente",loc="left",pad=20)
    from matplotlib.patches import Patch
    handles=[Patch(facecolor=c,label=LABELS[h]) for h,c in colors.items() if h in set(closed.hospital_origen)]
    lh,ll=ax.get_legend_handles_labels()
    ax.legend(handles+lh,[h.get_label() for h in handles]+ll,ncol=3,loc="upper left",fontsize=10)
    ax.set_ylim(0,max(closed.respuesta_total_s.max()*1.4,1) if len(closed) else 1)
    guardar(fig,"04_respuesta",f"Solo misiones cerradas: n={len(closed)}; censuradas={result['censurados']}. Respuesta total = espera + desplazamiento; p90 interpolado linealmente.")


def hospitales(a,h,folder):
    fig,axes=plt.subplots(1,2,figsize=(12,6))
    y=np.arange(len(h))
    axes[0].barh(y-.18,h.stock_inicial,height=.34,color="#B9CAD6",label="Inicial")
    axes[0].barh(y+.18,h.stock_final,height=.34,color=TEAL,label="Final")
    axes[0].set_yticks(y,[LABELS[v] for v in h.hospital]);axes[0].invert_yaxis()
    axes[0].set(xlabel="Ambulancias disponibles [unidades]",title="La flota cambia de base")
    axes[0].legend()
    axes[0].xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    vals=h.utilizacion_ref_pct.fillna(0)
    axes[1].barh(y,vals,color=[PALETTE[i] for i in range(len(h))])
    for i,(_,row) in enumerate(h.iterrows()):
        label=f"{row.utilizacion_ref_pct:.1f}%" if pd.notna(row.utilizacion_ref_pct) else "N/A · stock inicial 0"
        axes[1].text(vals.iloc[i]+.5,i,label,va="center",fontsize=11)
    axes[1].set_yticks(y,[LABELS[v] for v in h.hospital]);axes[1].invert_yaxis()
    axes[1].set(xlabel="Ocupación / (3 h × stock inicial) [%]",title="Carga atribuida al hospital de salida",xlim=(0,max(vals.max()*1.45,25)))
    guardar(fig,"05_hospitales","Índice de la guía: incluye misiones hasta el cierre. Con flota móvil no es una probabilidad de ocupación; no se divide por cero.")
    closed=a[a.estado=="cerrado"]
    mat=pd.crosstab(closed.hospital_origen,closed.hospital_retorno).reindex(index=h.hospital,columns=h.hospital,fill_value=0)
    mat.to_csv(TAB/"migracion.csv")
    fig,axes=plt.subplots(1,2,figsize=(12,5.8))
    im=axes[0].imshow(mat.values,cmap="Blues",vmin=0)
    for i in range(len(h)):
        for j in range(len(h)):
            if mat.iloc[i,j]:
                axes[0].text(j,i,str(mat.iloc[i,j]),ha="center",va="center",color="white" if mat.iloc[i,j]>mat.values.max()/2 else NAVY)
    labels=[LABELS[v] for v in h.hospital]
    axes[0].set_xticks(range(len(h)),labels,rotation=45,ha="right",fontsize=10)
    axes[0].set_yticks(range(len(h)),labels,fontsize=10)
    axes[0].set(xlabel="Hospital de retorno",ylabel="Hospital de salida",title="Misiones cerradas [conteo]")
    axes[0].grid(False)
    stock=pd.read_csv(folder/"stock_tiempo.csv")
    for ident,g in stock.groupby("hospital",sort=False):
        axes[1].step(g.t/60,g.disponibles,where="post",label=LABELS[ident],color=PALETTE[list(LABELS).index(ident)],alpha=.85)
    axes[1].set(xlabel="Tiempo [min]",ylabel="Disponibles [unidades]",title="Stock por hospital")
    axes[1].yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    axes[1].legend(ncol=2,fontsize=10,loc="upper left")
    guardar(fig,"06_migracion","Las unidades vuelven a la cola del hospital destino. Las líneas muestran disponibilidad, no propiedad fija de las ambulancias.")


def comparaciones():
    results=[]
    for path in sorted((ROOT/"salida").glob("*/accidentes.csv")):
        if path.parent.name in ["repeticion","smoke","denegacion_total","gui"]:
            continue
        _,_,r=resumen(path.parent)
        results.append(dict(escenario=r["carpeta"],semilla=r["semilla"],politica=r["retorno"],tasa=r["tasa"],
            accidentes=r["accidentes"],cerrados=r["cerrados"],censurados=r["censurados"],
            mediana_s=r["respuesta_total"]["mediana"],p90_s=r["respuesta_total"]["p90"],
            espera_media_s=r["espera"]["media"],migracion_pct=r["migracion_pct"],teleports=r["teleports"]))
    df=pd.DataFrame(results)
    df.to_csv(TAB/"comparacion_escenarios.csv",index=False)
    if len(df)<2:
        return
    fig,axes=plt.subplots(1,2,figsize=(12,5.7))
    for i,(policy,g) in enumerate(df[df.tasa==5].groupby("politica")):
        for ax,key in zip(axes,["mediana_s","p90_s"]):
            ax.scatter(np.full(len(g),i),g[key],color=PALETTE[i],s=55,zorder=3)
            ax.hlines(g[key].mean(),i-.18,i+.18,colors=NAVY,lw=3)
            ax.annotate(f"n={len(g)}",(i,g[key].max()),xytext=(12,4),textcoords="offset points",fontsize=10)
    policies=sorted(df[df.tasa==5].politica.unique())
    for ax,title in zip(axes,["Mediana por corrida","P90 por corrida"]):
        ax.set_xticks(range(len(policies)),["Retorno al más cercano" if p=="cercano" else "Retorno al origen" for p in policies])
        ax.set(title=title,ylabel="Respuesta total [s]",xlim=(-.55,len(policies)-.45))
    guardar(fig,"07_extension","Cada punto es una corrida; línea oscura = media entre semillas. Demanda fija; tráfico, flota y agenda se identifican por semilla.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--principal",type=Path,default=ROOT/"salida/principal")
    args=parser.parse_args()
    estilo()
    a,h,r=resumen(args.principal)
    net,shapes=red_geometria()
    mapa(a,args.principal,shapes)
    macro(net)
    respuesta(a,r)
    hospitales(a,h,args.principal)
    comparaciones()
    print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
