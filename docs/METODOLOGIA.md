# Método, supuestos y alcance

## Qué se reproduce

El documento de referencia es `Reto_Ambulancias_Docente_RVH.pdf`, 30 láminas,
Universidad de Cuenca, Redes Vehiculares y Heterogéneas. La implementación cubre
F0–F5, validaciones A/B, el experimento de `speedMode`, retorno al origen frente
al hospital más cercano y aumento de incidentes a 15/h.

**La entrega actual usa la red docente**: `cuenca_net.zip`, incorporado el
26 de octubre de 2026, contiene únicamente `cuenca_net.xml`. El ZIP original y
sus huellas se conservan en `datos/docente/` y `datos/procedencia_red.json`.
La red completa tiene 34.256 aristas; el recorte produce 1.745 aristas y 176
semáforos, coincidentes con la guía. La primera ejecución con red OSM alternativa
queda como respaldo local en `historial/Entrega_OSM_20261021.zip`, fuera de la entrega.
El ZIP no incluye la tabla de coordenadas, `vtypes.add.xml` ni `gen_fondo.sh`:
se mantienen los puntos OSM documentados y los tipos implementados en el proyecto.
Las cifras de la guía (por ejemplo, mediana 278 s) son una referencia ajena y
no se presentan como resultados de esta ejecución. Tampoco se pretende reproducir
exactamente sus parámetros de vehículos, su versión 1.28 ni sus tiempos de respuesta.

La ejecución usa **SUMO 1.12.0** de la imagen local `van3twin:jammy`. El PDF
también da ejemplos de esa versión. El análisis se ejecuta en el anfitrión.
El mapa se distribuye bajo ODbL: © OpenStreetMap contributors.

## F0: importación y reducción

Sobre la red completa del ZIP, **un solo `netconvert -s`** aplica los filtros
de la lámina 5 a esa red. No hay poda manual ni eliminación posterior de calles.
El recorte usa lon/lat `-79.030,-2.930,-78.950,-2.860`. Se mantienen vías tertiary
o superiores, su mayor componente débil, sin aristas aisladas; se simplifica
geometría y se unen cruces a 25 m. Los giros en U solo se permiten en terminales.

`km_arista` suma longitudes de aristas dirigidas externas: no es la longitud
geográfica de calles únicas. `km_carril` multiplica por número de carriles.
Los nodos excluyen nodos internos de cruce. La conectividad débil se obtiene por
recorrido del grafo no dirigido; **no equivale a conectividad dirigida por clase**.

## F1: demanda y lectura macro

Durante 10.800 s se solicitan 1.200 autos/h, 100 buses/h y 300 motos/h. Las tres
llamadas a `randomTrips.py --validate` usan semilla 42 y periodos 3, 36 y 12 s.
Las rutas no conectadas se descartan. La simulación dura 12.600 s: tres horas de
demanda y media hora de vaciado. Se elimina el `vType` duplicado de las rutas.

Los tipos reconstruidos usan Krauss con `tau >= 1 s`. La moto tiene menor `tau`
y mayor aceleración y factor de velocidad; es el tipo más agresivo sin que eso
autorice a ignorar la velocidad segura. La ambulancia respeta semáforos y reglas
normales; no se activa `bluelight` ni prioridad 7 en el escenario principal.

La línea base corre sin TraCI. `time-to-teleport=-1` y
`time-to-teleport.disconnected=-1` impiden retirar bloqueos por teletransportación.
`collision.action=warn` mantiene accidentados; `collision.mingap-factor=0`
exige contacto físico en la detección; se incluyen cruces. El 30% de vehículos
está equipado con rerouting cada 120 s. `ignore-junction-blocker=60` es el
parámetro de la guía, no una solución física calibrada para todos los cruces.

En cada intervalo de 900 s: `q = entered * 3600 / 900` [veh/h],
`k = density` [veh/km de arista, todos los carriles],
`v = speed * 3.6` [km/h]. Para la red y las avenidas, q y k se ponderan por
longitud; v se pondera por q. Las aristas vacías conservan peso espacial y
aportan q=k=0; no se les inventa velocidad observada. La velocidad agregada es
cero si no existen entradas en todo el intervalo.

Se calcula además la media ponderada de `k_e*v_e` y el error relativo frente a q.
**El producto de dos medias con pesos distintos no debe igualarse por fuerza a
la media del producto.** `entered` tampoco incluye las salidas de origen dentro
de la arista. Semáforos, acumulación y ventanas finitas explican diferencias.
El régimen estacionario se estudia de 900 a 10.800 s; cada avenida se agrupa
por su nombre real, sin incluir Panamericana en Las Américas. Una media baja
de densidad no descarta colas locales; no se ajusta una curva de capacidad con
una sola demanda.

## F2: hospitales y colas

`datos/hospitales.csv` conserva coordenadas WGS84, nombres, clasificación
usada en el ejercicio y procedencia de cada punto. Seis instalaciones usan
OpenStreetMap: centroides de área, salvo El Valle, que es un nodo. Patamarca
usa el centro de la celda del Plus Code `679342M9+H35`, obtenido de la ficha
de Google Maps aportada por el autor el 26 de octubre de 2026. Esos puntos
representan instalaciones, no entradas de urgencias verificadas en campo.

Se llama `convertRoad(lon, lat, isGeo=True, vClass='emergency')`. Se conserva
esa proyección original y su distancia. Se comprueba una ruta de ida y otra
de vuelta respecto a VCM. Si el ramal más próximo no permite ambas, se elige
el carril emergency más próximo que sí las permite. La tabla conserva ambas
aristas y distancias: la corrección es visible, no se modifican las coordenadas
para conseguir un umbral. Se validan los 49 pares dirigidos entre hospitales.
El umbral docente es estrictamente menor de 150 m. El centroide OSM original
de Patamarca daba 158,08 m. La captura aportada incluye el código `42M9+H35`,
recuperado con referencia Cuenca (−2,9; −79,0) mediante Open Location Code.
Su centro es latitud −2,866112500 y longitud −78,982265625; proyectado con TraCI
queda a **135,32 m** de la misma arista `378364650#0` (Vía Checa Chiquintad).
Las cuatro esquinas de la celda quedan como máximo a 137,12 m. La calle Del Camal
sigue excluida por el filtro vial: no se modificó la red ni el umbral.

La dirección del hospital se corrobora en su [directorio oficial](https://www.hospitalmunicipalcuenca.gob.ec/directorio-telefonico/).
La captura, la coordenada anterior y la nueva, los límites de celda y las
huellas quedan en `datos/patamarca_ubicacion.json`. `make ubicacion` reproduce
la decodificación y confirma los siete hospitales dentro del límite y los 49
pares alcanzables. Se repitieron todas las corridas que dependen de hospitales,
la comparación pareada, la repetición, la prueba negativa y las capturas GUI.
La red, la demanda y la línea base no dependen de esta coordenada y se conservaron.

Cada hospital tiene una cola `deque` FIFO. Con semilla 42, los cinco públicos
obtienen `[3,1,1,3,2]` unidades y los dos privados `[0,0]`. No representa una
medición de la flota real. Los identificadores U01–U10 persisten al migrar.
La negativa de disponibilidad es Bernoulli con p=0,25, solo si hay stock.
Se registran por separado negativa aleatoria, cola vacía y falta de ruta.

Se usan generadores locales separados: flota `seed`, agenda `seed+1`, selección
de bus `seed+2` y disponibilidad `seed+3`. Así, agregar un sorteo de agenda no
cambia accidentalmente la flota. La semilla también controla SUMO. Las rutas de
fondo se mantienen fijas (semilla de demanda 42) en las comparaciones.

## F3: agenda y choques observados

Por hora se programan cinco instantes uniformes del minuto 5 al 58, redondeados
al siguiente segundo. Se buscan buses fuera de cruces, a más de 60 m del inicio,
con velocidad entre 4 y 18 m/s y margen para que el alcance ocurra en la misma
arista. No se repiten deliberadamente aristas. Se comprueba antes que emergency
pueda ir y volver: la red puede contener terminales accesibles a
un viaje de bus pero sin retorno útil para la ambulancia. Esto restringe el
universo espacial de los incidentes programados y se declara como supuesto.

Una moto nueva se inserta 45 m detrás, en el mismo carril y siguiendo el resto
de la ruta del bus. Se activa solo después de aparecer en la lista de vehículos:
`setSpeedMode(0)`, `setLaneChangeMode(0)`, `setSpeed(22)`. No se usa `moveTo` ni
un contacto creado modificando posiciones. La colisión debe ser emitida por
SUMO y aparecer en `colisiones.xml`. Se detecta con `getCollisions()`, distinguiendo
bus y moto por clase; cada pareja se procesa una sola vez.

Si no hay bus apto se reintenta en 20 s. Si el intento expira (90 s), desaparece
la moto o la pareja abandona la arista, se restaura el control y se cancela la
moto insertada; se reprograma en 60 s. Por ello cinco instantes programados no
implican exactamente cinco colisiones observadas dentro de cada hora.

La parada es de dos pasos: modo 0 + velocidad 0, luego modo 31 + velocidad 0.
Los accidentados se pintan de rojo y se crea un POI amarillo. Otras colisiones
se registran y se retiran sus vehículos, excepto ambulancias y accidentados
protegidos. Estas retiradas son una intervención del controlador, **no** un
teleport. El contador se entrega y limita la comparación con la línea base.

En una vía recta aislada se ensayan modos 31, 30, 23 y 0 con idénticos vehículos.
La única variable experimental es el bitset. El bit 0 controla la velocidad
segura. Modo 30 conserva otras restricciones y desactiva ese bit; modo 23
desactiva la prioridad de aproximación, pero conserva `v_safe`. El modo 0
es el comportamiento heredado, no literalmente todos los controles desactivados:
los bits 5 y 6 tienen semántica invertida en la documentación de SUMO.

## F4: selección, atención y retorno

Se ordenan hospitales alcanzables por `findRoute(..., vType='ambulance',
routingMode=ROUTING_MODE_AGGREGATED)`, que usa tiempos suavizados de tráfico.
Se recorre el ranking hasta encontrar una cola con stock que conceda la unidad.
Se guardan ETA, rango, stock y resultado de cada candidato. Sin disponibilidad,
el incidente queda pendiente y se reintenta cada 30 s.

SUMO 1.12 calcula la ETA entre aristas completas: no es una promesa exacta de
viaje entre dos posiciones interiores. La ambulancia parte en la proyección
del hospital. El instante de despacho incluye cualquier retraso de inserción
posterior; no se cuenta como viaje gratuito ni se fuerza su inserción.

La llegada se observa por: distancia de conducción no negativa ≤50 m; detención
en la misma arista detrás del incidente; detención ≥30 s y distancia euclídea
≤300 m (aproximación a pie). Si terminó su ruta, se registra `fin_ruta` de forma
explícita. Se omiten aristas internas hasta el siguiente paso. Cada 60 s se
recalcula la ruta si queda a más de 300 m por carretera o no hay distancia válida.
El criterio a pie marca llegada del equipo; no modela explícitamente personas
ni añade tiempo de caminata, por lo que puede subestimar el acceso final.

Después de 120 s se retiran bus y moto, se elimina el POI, y se elige el hospital
con menor tiempo desde la arista del accidente, independientemente de su stock.
Se restauran los tres controles: `setSpeedMode(31)`, `setLaneChangeMode(1621)` y
`setSpeed(-1)`, y se aplica `changeTarget`. Si la ambulancia ya acabó su ruta,
se reinserta para retornar, manteniendo el identificador de unidad. Se considera
disponible al terminar la arista hospitalaria (`arrivalPos=max`, limitación de
esta representación por aristas). Ninguna unidad regresa a la cola antes de
la llegada de SUMO. Se verifica conservación e identidad de la flota cada segundo.

## F5: indicadores y censura

- Espera = despacho − accidente.
- Desplazamiento = llegada − despacho.
- **Respuesta total = llegada − accidente = espera + desplazamiento.**
- Misión = disponible − despacho.
- Migración = fracción de misiones cerradas cuyo retorno difiere del origen.
- Índice docente de utilización = segundos ocupados atribuidos al hospital de
  salida / (10.800 × stock inicial). Se entrega también ocupación recortada a
  las primeras tres horas. Con stock inicial cero se usa N/A, nunca infinito.

La guía llama «respuesta» al tiempo desde el accidente en la lámina 21 y al
tiempo desde despacho en la 25. Los CSV conservan ambas definiciones. Mediana,
media, p90 y máximo se calculan solo sobre misiones **cerradas**, con n explícito;
el p90 usa interpolación lineal. Las misiones abiertas siguen en los CSV con
estado, tiempos no observados −1 e indicadores derivados vacíos. No se eliminan
del denominador de incidentes ni se les asigna duración cero. Si hay censura,
la distribución de las cerradas puede ser optimista y no caracteriza todos los
incidentes.

La utilización es una normalización de carga según la guía; con flota migratoria
no es una probabilidad física de ocupación de una flota fija y podría superar
100%. Se conserva el balance inicial + recibidas − despachos = final por hospital.

## Extensión y alcance de las conclusiones

Se comparan retorno al más cercano y retorno al origen para semillas
8, 21, 42, 84 y 123. Comparten demanda, parámetros, flota inicial y agenda por
semilla. Las decisiones de retorno cambian el tráfico: pueden cambiar el bus
seleccionado, las colisiones y la secuencia efectiva de disponibilidad. Son
**corridas emparejadas por semilla, no incidentes idénticos emparejados**.
Los cinco resultados por política se presentan individualmente; no se declara
significancia con una sola ejecución ni se reutiliza cada incidente como una
réplica independiente. Una corrida adicional con 15/h explora carga; su efecto
no es una garantía sobre un servicio de emergencias real.

La semilla 7 con retorno al origen abortó a los 7.815 s por una aserción interna
de `MSVehicle::getBackPositionOnLane` en SUMO 1.12.0. Sus resultados incompletos
se excluyeron. Se eligió la semilla 8 para ambas políticas antes de conocer sus
resultados. `salida/fallos/origen_s7_t5/` conserva los parámetros y el log.
La corrida cercana/7 se mantiene como diagnóstico local y no entra en los cinco pares.

## Referencias técnicas

1. Guía docente local, láminas 4–12, 14–18, 20–23 y 25–29.
2. [Control de vehículos y bits de speedMode](https://sumo.dlr.de/docs/TraCI/Change_Vehicle_State.html).
3. [Pesos de tiempo y modos de enrutamiento](https://sumo.dlr.de/docs/Simulation/Routing.html).
4. [Variables de simulación y conversiones](https://sumo.dlr.de/docs/TraCI/Simulation_Value_Retrieval.html).
5. [Datos agregados por arista](https://sumo.dlr.de/docs/Simulation/Output/Lane-_or_Edge-based_Traffic_Measures.html).
6. [Licencia y atribución OpenStreetMap](https://www.openstreetmap.org/copyright).
7. Coordenadas y consulta: `datos/hospitales.csv`, `datos/procedencia_osm.json`.

Las referencias online se contrastaron durante la implementación; las firmas
de funciones y las opciones se comprobaron además en SUMO 1.12 instalado.
