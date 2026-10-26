# Diccionario de salidas

## `accidentes.csv`

Una fila por colisión bus–moto única detectada. Tiempos absolutos en segundos
desde el inicio de SUMO; `-1` significa que el evento no ocurrió antes del corte.
Las duraciones derivadas no observadas se dejan vacías.

| Campo | Significado |
|---|---|
| `id`, `bus`, `moto` | Identificadores del incidente y de los vehículos implicados |
| `plan_id`, `t_programado` | Instante de la agenda que originó el intento; 0/−1 si es natural |
| `t_accidente`, `tipo_colision` | Detección TraCI y clase `collision` o `junction` |
| `edge`, `pos` | Destino externo utilizable para la ambulancia; posición en m |
| `x`, `y` | Coordenadas locales del bus en el choque; referencia para distancia a pie |
| `estado` | espera, en_camino, atendiendo, retorno o cerrado |
| `hospital_origen`, `hospital_retorno` | Bases de salida y recepción |
| `unidad`, `vehiculo` | Identidad persistente de flota y vehículo SUMO de la misión |
| `t_despacho`, `t_llegada`, `t_retorno`, `t_disponible` | Hitos observados de la máquina de estados |
| `eta_s`, `ruta_m`, `rango_hospital` | Predicción de viaje por ruta, longitud y rango de ETA seleccionado |
| `criterio_llegada` | carretera_50m, cola_misma_arista, a_pie_300m o fin_ruta |
| `espera_s` | t_despacho − t_accidente |
| `desplazamiento_s` | t_llegada − t_despacho |
| `respuesta_total_s` | t_llegada − t_accidente |
| `mision_s` | t_disponible − t_despacho |

## `hospitales.csv`

Una fila por hospital. `stock_inicial` y `stock_final` son unidades disponibles;
`despachos` y `recibidas` son conteos. `rechazos` cuenta negativas aleatorias
con stock; `sin_stock` cuenta candidatos sin unidad durante los intentos.
`ocupado_s` atribuye al hospital de salida la duración de sus misiones, incluidas
abiertas hasta el corte. `ocupado_3h_s` recorta esa duración al horizonte 10.800 s.
`utilizacion_ref_pct` y `utilizacion_3h_pct` dividen respectivamente por
10.800 × stock inicial; si este es cero, ambas quedan vacías (N/A).

## Evidencia complementaria

| Archivo | Uso |
|---|---|
| `hospitales_ubicados.csv` | Punto WGS84, proyección inicial convertRoad, acceso corregido, distancias, carril y calle |
| `conectividad_hospitales.csv` | 49 pares de hospitales, alcanzabilidad dirigida y ETA libre |
| `decisiones.csv` | Cada candidato por incidente e intento: rango ETA, stock y resultado |
| `stock_tiempo.csv` | Unidades disponibles por hospital cada minuto |
| `remanentes.csv` | Vehículos aún activos al cierre, con arista, espera y velocidad |
| `eventos.log`, `eventos.jsonl` | Cronología textual y estructurada |
| `parametros.json` | Semillas, agenda, configuración, versión SUMO y huellas de entradas/código |
| `ejecucion.json` | Contadores finales, pendientes, retiradas de fondo y tiempo de pared |
| `colisiones.xml` | Detecciones físicas emitidas por SUMO; puede repetir una pareja |
| `tripinfo.xml` | Viajes, incluidas filas inconclusas cuando corresponde |
| `summary.xml`, `estadisticas.xml` | Estado global y resumen independiente del simulador |
| `validacion.json` | Lista de controles, resultado, nivel y evidencia |
| `resumen.json`, `resumen.txt` | Estadísticos calculados a partir de misiones cerradas |

`salida/base/macro.xml` es exclusivo de la línea base. En las corridas TraCI se
sobrescribe la lista de adicionales para cargar solo los tipos: así no se pisa
accidentalmente el archivo macro de la línea base.

## Procedencia y presentación

`datos/procedencia_red.json` identifica el ZIP docente y el XML original por
SHA-256. `parametros.json` enlaza cada corrida con la red, los hospitales,
el controlador y los archivos de escenario utilizados.

`salida/visual/verificacion_visual.json` registra los siete POI, las velocidades
del bus y la moto, el vehículo de fondo detenido y la unidad que regresó a otra
base. Conserva stock antes/después del retorno y huellas de las tres capturas.
La auditoría comprueba que esos archivos correspondan a la red y al controlador
actuales. Las imágenes se escriben en el siguiente paso de SUMO al solicitarlas;
`t_s` identifica el estado TraCI que motivó la captura.

`docs/autor.json` contiene los datos de autor proporcionados por el estudiante.
`docs/latex/datos.tex` y `tabla_*.tex` se generan desde los resultados; la prosa
del informe está en `Informe_Reto_Ambulancias.tex`.
