# Guía de reproducción, paso por paso

Todos los comandos parten de la raíz `RetoAmbulancia`. No hacen falta ns-3,
redes móviles ni iniciar los contenedores de otros talleres: el reto usa SUMO
y TraCI. El script `en_docker.sh` crea un contenedor efímero, con tu UID/GID,
monta solo esta carpeta como `/work` y conserva las salidas en el anfitrión.

## 0. Revisar el entorno

```bash
cd /home/angel/v2x/van3twin-docker/RetoAmbulancia
docker image ls van3twin:jammy
./scripts/en_docker.sh sumo --version
./scripts/en_docker.sh netconvert --version
./scripts/en_docker.sh python3 -c 'import sys; sys.path.append("/usr/share/sumo/tools"); import traci, sumolib; print(traci.__file__)'
python3 --version
tectonic --version
```

Entorno ejecutado: SUMO 1.12.0, Python 3.10 dentro del contenedor y Python 3.13.12
para análisis en el anfitrión. El contenedor no necesita interfaz gráfica para
generar resultados. Su imagen fue proporcionada por el proyecto padre; para
construirla desde cero se puede seguir el README y Dockerfile de `../`.
Ese build completo no forma parte de la validación de este reto.

Crear el entorno de análisis, si hace falta:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

El informe se compila con **Tectonic 0.16.9**. Si no está instalado, usa los
[binarios o instrucciones oficiales](https://tectonic-typesetting.github.io/en-US/install.html).
La primera compilación descarga los paquetes LaTeX necesarios; las siguientes
reutilizan la caché `/tmp/reto-tex-cache`. No se necesita ReportLab.

En los comandos siguientes, sustituir `python3` por `.venv/bin/python` **solo
fuera del contenedor**, si se instaló el entorno virtual. Para Make:
`make reproducir PYTHON=.venv/bin/python`. Dentro del contenedor siempre se usa
su propio `python3`, que ya conoce la instalación de SUMO.

## 1. Datos de entrada y procedencia

La reproducción recomendada usa los archivos archivados. No requiere red:

```bash
cat datos/procedencia_red.json
cat datos/hospitales.csv
sha256sum datos/docente/cuenca_net.zip datos/cuenca_net.xml
```

El ZIP docente está incorporado y contiene únicamente `cuenca_net.xml`.
Para repetir su incorporación, con validación del XML y registro SHA-256:

```bash
python3 scripts/importar_red.py datos/docente/cuenca_net.zip
```

Para incorporar el archivo originalmente descargado en este equipo:

```bash
python3 scripts/importar_red.py /home/angel/Downloads/cuenca_net.zip
```

El XML OSM archivado sirve para la procedencia de los puntos hospitalarios;
no se vuelve a importar como red. Si se recibe la tabla del capítulo,
reemplazar en `datos/hospitales.csv` los puntos por coordenadas verificadas y
documentar su fuente y método. Si se proporciona, incorporar también el archivo
`escenario/vtypes.add.xml`. Mantener
las columnas `id,nombre,tipo,lon,lat` y los identificadores de tipo
`car,bus,moto,ambulance`. Después regenerar demanda, simulaciones y análisis.
Con las coordenadas actuales, Patamarca queda a 158,08 m y A3 sigue parcial.
Después de corregir ese dato con una fuente válida, ejecutar `make reproducir`,
`make gui-validar`, `make validar informe` y volver a empaquetar. La distancia
debe ser estrictamente menor de 150 m: no se cambia el umbral de la auditoría.

## 2. F0: derivar las avenidas

```bash
./scripts/en_docker.sh python3 scripts/preparar.py red
cat salida/preparacion/redes.csv
```

`scripts/preparar.py` ejecuta un solo `netconvert -s`, con los filtros completos
del PDF. El comando exacto y las huellas se conservan en
`salida/preparacion/red.json`; el log está en `netconvert.log`.
La red derivada es `escenario/cuenca_ciudad.net.xml`.

## 3. F1: generar tráfico

```bash
./scripts/en_docker.sh python3 scripts/preparar.py demanda --seed 42
cat salida/preparacion/demanda.csv
```

Genera `fondo_car.rou.xml`, `fondo_bus.rou.xml` y `fondo_moto.rou.xml`, además de
los viajes intermedios. En SUMO 1.12 se usa `--vclass` para filtrar permisos y
`type="..."` para seleccionar el tipo ya definido. `--vehicle-class` junto
con `type` es incompatible. El script elimina definiciones vType duplicadas.

## 4. F1: línea base sin TraCI

```bash
./scripts/en_docker.sh python3 scripts/linea_base.py
cat salida/base/resumen.json
```

Ejecuta `sumo -c escenario/reto.sumocfg`. Salidas: `estadisticas.xml`,
`tripinfo.xml`, `colisiones.xml`, `summary.xml` y `macro.xml`, más logs.
`macro.add.xml` usa `freq="900"`, compatible con SUMO 1.12.
La ejecución entregada tarda aproximadamente medio minuto; depende del equipo.

## 5. F2–F4: hospitales, accidentes y despacho

```bash
mkdir -p salida/principal
./scripts/en_docker.sh python3 scripts/reto_ambulancias.py \
  --seed 42 --tasa 5 --p-sin 0.25 --retorno cercano \
  --end 12600 --output salida/principal \
  > salida/principal/ejecutor.log 2>&1
```

Mientras corre, en otra terminal:

```bash
tail -f salida/principal/eventos.log
```

Al terminar:

```bash
cat salida/principal/ejecucion.json
cat salida/principal/hospitales_ubicados.csv
cat salida/principal/hospitales.csv
```

`ACCIDENTE`, `CANDIDATO`, `DESPACHO`, `LLEGADA`, `RETORNO` y `DISPONIBLE`
permiten seguir una misión. `eventos.jsonl` entrega la misma evidencia en formato
estructurado. No confundir avisos de colisiones esperadas con un aborto del
programa: el comando debe terminar con código 0 y generar los CSV finales.

## 6. F5: analizar y exportar gráficas

```bash
python3 scripts/analisis.py
cat salida/principal/resumen.txt
cat salida/tablas/avenidas.csv
```

Exporta cada figura a PNG (220 dpi), SVG y PDF. SVG/PDF son vectoriales para
presentaciones e impresión. Las tablas macro, avenidas, migración y escenarios
quedan en `salida/tablas/`. Se puede regenerar el análisis sin volver a simular.

## 7. Extensión: retorno al origen, cinco semillas

```bash
./scripts/en_docker.sh python3 scripts/lote.py \
  --semillas 8 21 42 84 123 --politicas cercano origen
```

La combinación cercano/42 ya es `principal`, por lo que el lote ejecuta las otras
nueve. Son diez corridas científicas, cinco por política. Cada una guarda su
propia carpeta y `ejecutor.log`. No se sobreescribe la línea base. En conjunto
requieren varios minutos.

## 8. Extensión de carga: 15 accidentes/h

```bash
./scripts/en_docker.sh python3 scripts/lote.py \
  --semillas 42 --politicas cercano --tasa 15
```

Su salida es `salida/cercano_s42_t15/`. Examinar incidentes, misiones cerradas,
esperas, pendientes al corte y conservación de flota; no asumir que todo cierra
solo porque el programa terminó correctamente.

## 9. Experimento causal de speedMode

```bash
./scripts/en_docker.sh python3 scripts/experimento_modos.py
cat salida/modos/resultados.csv
```

Usa una vía recta separada, con bus y moto iguales en los cuatro ensayos.
Comprueba automáticamente que 31 y 23 no chocan, mientras 30 y 0 sí. Conserva
los XML de colisión y logs de cada modo. No afecta el escenario de Cuenca.

## 10. Repetición exacta y auditoría

```bash
./scripts/en_docker.sh python3 scripts/lote.py --repeticion
python3 scripts/comprobar_repeticion.py
python3 scripts/validar.py --todos
python3 -m unittest discover -s pruebas -v
```

La repetición compara SHA-256 de siete CSV/logs deterministas, no archivos XML
con fecha de generación ni el tiempo de pared. `reproducibilidad.json` conserva
las dos huellas de cada archivo. La auditoría retorna código distinto de cero
si falla una invariante; las advertencias espaciales o de censura se muestran y
se conservan. Los tests comprueban además que la auditoría rechace una unidad
inventada, una respuesta alterada y un accidente sin colisión física.

Para ejecutar la prueba negativa de disponibilidad total antes de los tests:

```bash
make denegacion
python3 -m unittest discover -s pruebas -v
```

Esta prueba usa `p_sin=1` y finaliza a los 1.200 s deliberadamente con incidentes
en espera. Comprueba reintentos cada 30 s, tiempos no inventados y conservación
de stock. Se excluye de la comparación estadística de políticas; las advertencias
de misiones abiertas y tráfico restante en esta carpeta son esperadas.

## 11. Informe final

```bash
python3 scripts/analisis.py
python3 scripts/informe.py
```

Genera `docs/Informe_Reto_Ambulancias.pdf` y `docs/RESULTADOS.md` con valores de
los archivos reales. El PDF usa IEEEtran en A4 y doble columna. Los datos y
tablas se exportan a `docs/latex/` y Tectonic compila la fuente del artículo.
El registro está en `docs/latex/build/compilacion.txt`; `compilacion.json`
conserva las huellas del `.tex`, los datos y el PDF.
El informe incluye gráficas, método, resultados, validación,
limitaciones y comandos esenciales. El presente documento contiene los comandos
completos y `METODOLOGIA.md` detalla las decisiones de implementación.

Para compilar únicamente el LaTeX ya preparado, desde la raíz:

```bash
cd docs/latex
mkdir -p build
XDG_CACHE_HOME=/tmp/reto-tex-cache tectonic --untrusted --keep-logs --outdir build Informe_Reto_Ambulancias.tex
```

Regresa a la raíz con `cd ../..` antes de los pasos siguientes. Las instrucciones
de la clase, la redacción y el paquete editable están en `docs/latex/README.md`.

## 12. Inspección en SUMO-GUI

La entrega incluye una ejecución real de SUMO-GUI con capturas y estados TraCI
en `salida/visual/`. Para repetirla durante tu exposición:

```bash
./scripts/demo_gui.sh
```

Abre Remmina u otro visor VNC y conéctate a **localhost:5902**. El puerto se
publica solo en tu equipo. El script arranca SUMO-GUI automáticamente y se
detiene en tres momentos; después de revisar cada uno, pulsa Enter en la terminal:

1. **Hospitales:** siete POI y stock inicial, incluidos los dos privados en cero.
2. **Accidente y cola:** bus y moto inmóviles, en rojo, con tráfico detenido detrás.
3. **Retorno:** la unidad ya está disponible en un hospital distinto del de salida;
   la terminal muestra el identificador y el stock receptor.

Las capturas `01_hospitales.png`, `02_accidente_cola.png`, `03_retorno.png` y
`verificacion_visual.json` se regeneran con los estados realmente observados.
El retorno se comprueba además en `salida/visual/ejecucion/eventos.log`:
la ambulancia deja de circular al incorporarse a la cola hospitalaria.
La ejecución automática usa el mismo controlador y los mismos eventos:

```bash
./scripts/demo_gui.sh --automatico
python3 scripts/validar.py --todos
```

Esta comprobación técnica ya está realizada; la presentación y valoración ante
el docente debes hacerlas tú. Las capturas son apoyo, no sustituyen la exposición.
Si el puerto está ocupado: `RETO_VNC_PORT=5903 ./scripts/demo_gui.sh`, conectando
el visor a localhost:5903. `make gui` y `make gui-validar` son atajos equivalentes.

Para A1 explica que `junctions.join-dist=25` agrupa cruces próximos. Para B2
abre `decisiones.csv` y muestra un despacho con rango mayor que 1 y sus descartes
por stock o negativa. Para B3 señala en el código las tres restauraciones:
`setSpeedMode(31)`, `setLaneChangeMode(1621)` y `setSpeed(-1)`.

## 13. Empaquetar y comprobar integridad

```bash
python3 scripts/preparar_publicacion.py
python3 scripts/empaquetar.py
sha256sum -c MANIFEST.sha256
```

Genera `Entrega_Reto_Ambulancias.zip`, con datos, código, resultados, informe y
figuras, excluyendo entornos virtuales y metadatos del asistente. Se distribuye sin el respaldo histórico de la red alternativa. El ZIP se
comprueba con CRC y el manifiesto conserva huellas de cada archivo. Si se
regenera una simulación o un informe, volver a ejecutar el empaquetado para
actualizar las huellas. Este manifiesto comprueba integridad de la entrega;
`comprobar_repeticion.py` comprueba reproducibilidad de la simulación.

`preparar_publicacion.py` genera `Codigo_GitHub.zip`, la carpeta
`publicacion/github/`, `Informe_LaTeX.zip` y una copia del PDF con el nombre
`Practica04_AngelApolo_IEEE.pdf`. No publica nada remotamente. Para GitHub y
la carga en Talleres, sigue `docs/ENTREGA.md`.

## Problemas frecuentes

| Mensaje | Diagnóstico y acción |
|---|---|
| `permission denied ... docker.sock` | Habilitar Docker para la cuenta o ejecutar mediante el mecanismo de autorización del entorno. |
| `Unable to find image van3twin:jammy` | Construir/obtener la imagen del proyecto padre o definir `SUMO_IMAGE` con una instalación compatible. |
| `No module named traci` | Usar `en_docker.sh` para los scripts SUMO; no instalar otro cliente de versión distinta a ciegas. |
| `Another vehicle type ... exists` | Regenerar rutas con `preparar.py demanda`, que elimina los vType duplicados. |
| `No connection between edge ...` | Revisar conectividad dirigida por clase; el controlador registra descartes, no crea rutas ficticias. |
| Distancia hospitalaria >150 m | Consultar la tabla y el mapa: se requieren coordenadas/accesos docentes para equivalencia espacial estricta. |
| Figura sin datos de extensión | Ejecutar el lote y volver a generar análisis e informe. |
| Validación no pasa | Leer `validacion.json`; no cambiar umbrales ni suprimir filas para aparentar cumplimiento. |
