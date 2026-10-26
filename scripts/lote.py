#!/usr/bin/env python3
"""Corridas independientes; cada salida conserva sus parámetros y sus logs."""
import argparse
import subprocess
import sys
from entorno import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--semillas",nargs="+",type=int,default=[8,21,42,84,123])
    p.add_argument("--politicas",nargs="+",choices=["cercano","origen"],default=["cercano","origen"])
    p.add_argument("--tasa",type=int,default=5)
    p.add_argument("--repeticion",action="store_true")
    args=p.parse_args()
    jobs=[(42,"cercano",5,"repeticion")] if args.repeticion else [
        (seed,policy,args.tasa,f"{policy}_s{seed}_t{args.tasa}") for seed in args.semillas for policy in args.politicas]
    for seed,policy,rate,name in jobs:
        if seed==42 and policy=="cercano" and rate==5 and not args.repeticion:
            # La corrida principal ya representa esta combinación; evita duplicarla en la estadística.
            continue
        out=ROOT/"salida"/name
        out.mkdir(parents=True,exist_ok=True)
        command=[sys.executable,str(ROOT/"scripts/reto_ambulancias.py"),"--seed",str(seed),
                 "--retorno",policy,"--tasa",str(rate),"--output",str(out)]
        print(f"INICIO {name}",flush=True)
        with (out/"ejecutor.log").open("w") as log:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        print(f"TERMINADO {name}",flush=True)


if __name__=="__main__":
    main()
