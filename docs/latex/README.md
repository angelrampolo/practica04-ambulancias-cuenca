# Informe IEEE en LaTeX

Autor: Angel Ramiro Apolo Aguilar, Universidad de Cuenca.

`Informe_Reto_Ambulancias.tex` usa IEEEtran 1.8b en modo `conference`, papel A4
y doble columna. Se respetan la clase y sus márgenes; no se añade un sello de
publicación de IEEE. Los paquetes proporcionan ecuaciones, tablas `booktabs`,
figuras vectoriales, citas numeradas, enlaces y bloques de código.

Las cifras de `datos.tex` y las tablas `tabla_*.tex` se generan desde los CSV y
JSON reales. Para regenerar todo desde la raíz del proyecto:

```bash
python3 scripts/analisis.py
python3 scripts/validar.py --todos
python3 scripts/informe.py
```

Se verificó con Tectonic 0.16.9. Para compilar la fuente ya preparada:

```bash
cd docs/latex
mkdir -p build
XDG_CACHE_HOME=/tmp/reto-tex-cache tectonic --untrusted --keep-logs --outdir build Informe_Reto_Ambulancias.tex
```

Con una distribución LaTeX que incluya IEEEtran también se puede usar
`pdflatex Informe_Reto_Ambulancias.tex` dos veces, desde `docs/latex/`.
El ZIP de fuentes es autocontenido: dentro de `Informe_IEEE/` están el `.tex`,
la clase, los datos, `figuras/` y `capturas/`. Descomprímelo y ejecuta
`tectonic Informe_Reto_Ambulancias.tex` desde esa carpeta. En Overleaf carga
el contenido de `Informe_IEEE/` y elige `Informe_Reto_Ambulancias.tex` como
documento principal. Las dos rutas de gráficos están previstas en la fuente.

Fuentes de formato consultadas:

- [IEEE: herramientas y plantillas](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/).
- [IEEE: estructura de un artículo](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/).
- [Instalación de Tectonic](https://tectonic-typesetting.github.io/en-US/install.html).

La revisión de prosa aplica la skill pública
[Humanizador en español](https://github.com/donutinit/humanizador/blob/main/SKILL.md),
versión 1.0.0, en modo integrado: redacción neutra, frases concretas y conservación
de datos, referencias y limitaciones. No se modifican cifras para mejorar la narrativa.

`IEEEtran.cls` se conserva sin cambios desde el bundle v33 de Tectonic; su
cabecera contiene los créditos y la licencia LPPL 1.3 de la clase.
