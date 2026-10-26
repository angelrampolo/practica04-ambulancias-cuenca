# Entrega de la Práctica 04

Angel Ramiro Apolo Aguilar · angel.apolo@ucuenca.edu.ec.
Universidad de Cuenca, Ingeniería en Telecomunicaciones, 10.º ciclo.
Asignatura: Redes Vehiculares y Heterogéneas.

Plazo indicado: **miércoles 28 de octubre de 2026 a las 20:00**, hora local
America/Guayaquil. Destino: plataforma académica, sección **Talleres**.

## Archivos

| Archivo | Uso |
|---|---|
| `docs/Informe_Reto_Ambulancias.pdf` | Informe IEEE de doble columna para leer y entregar |
| `publicacion/Practica04_AngelApolo_IEEE.pdf` | Copia del mismo informe con nombre de entrega |
| `Informe_LaTeX.zip` | Fuente `.tex`, clase IEEEtran, tablas y figuras para recompilar |
| `Codigo_GitHub.zip` | Código, documentación, datos esenciales y resultados ligeros |
| `publicacion/github/` | Carpeta de código preparada para crear el repositorio propio |
| `Entrega_Reto_Ambulancias.zip` | Entrega completa con entradas, resultados y manifiesto SHA-256 |

Las tres capturas reales de SUMO-GUI están incluidas en el informe y se conservan
en `salida/visual/`: hospitales, accidente con cola y retorno. El archivo
`verificacion_visual.json` registra los estados y las huellas de las imágenes.

## Estado

- Red docente incorporada y simulaciones recalculadas.
- Código, capturas, gráficas y resultados preparados.
- Informe en LaTeX con IEEEtran y datos de autor.
- A3 verificado: Patamarca queda a 135,32 m con el Plus Code aportado por el autor; los siete hospitales cumplen menos de 150 m y conservan las 49 rutas dirigidas.
- Presentación de A y B ante el docente pendiente.
- GitHub: [repositorio público de código, informe y capturas](https://github.com/angelrampolo/practica04-ambulancias-cuenca).
- Enlace al repositorio incorporado como vínculo clicable en el apéndice del informe IEEE.
- Carga en Talleres pendiente de indicar el enlace y disponer de acceso a la plataforma.

El repositorio padre apunta a `Pbarbecho/van3twin-docker`, que es la fuente del
entorno docente. La carpeta `publicacion/github/` permite publicar el trabajo
en un repositorio propio sin cambiar ese remoto.

## Preparar y publicar el código

Desde `RetoAmbulancia`, para actualizar los archivos:

```bash
python3 scripts/analisis.py
python3 scripts/validar.py --todos
python3 scripts/informe.py
python3 scripts/preparar_publicacion.py
python3 scripts/empaquetar.py
sha256sum -c MANIFEST.sha256
```

El destino elegido es el repositorio público `angelrampolo/practica04-ambulancias-cuenca`.
Una vez creado en GitHub, estos comandos publican la carpeta preparada por primera vez:

```bash
cd publicacion/github
git init -b main
git config user.name 'Angel Ramiro Apolo Aguilar'
git config user.email 'angel.apolo@ucuenca.edu.ec'
git add .
git commit -m 'Práctica 04: accidentes bus-moto y despacho de ambulancias'
git remote add origin https://github.com/angelrampolo/practica04-ambulancias-cuenca.git
git push -u origin main
```

La autenticación se realiza con el mecanismo de GitHub configurado en tu equipo.
Después de publicar, comprueba que el repositorio abra y permita leer el código
y el README sin iniciar sesión, porque la visibilidad solicitada es pública.
Para actualizarlo después de cambiar archivos, ejecuta de nuevo el preparador,
crea un nuevo commit desde `publicacion/github/` y ejecuta `git push`.
La existencia del enlace en el informe no sustituye la comprobación de que la
publicación haya concluido.

## Cargar en Talleres

Abre el taller de la Práctica 04 y adjunta el PDF. Incluye el enlace real de
GitHub en el campo de texto o el lugar que pida la plataforma. Si admite anexos,
adjunta `Informe_LaTeX.zip` o la entrega completa según las instrucciones del aula.
Comprueba que el PDF cargado se abre, que los cambios quedaron guardados y que
el estado indique entrega enviada. Conserva el comprobante o captura final.

Esta guía no constituye un comprobante de publicación ni de entrega.
