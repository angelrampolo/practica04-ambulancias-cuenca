#!/usr/bin/env bash
set -euo pipefail
mkdir -p salida/visual/ejecucion
Xvfb :99 -screen 0 1600x1000x24 +extension GLX +render -noreset > salida/visual/xvfb.log 2>&1 &
x_pid=$!
trap 'kill "$x_pid" 2>/dev/null || true' EXIT
for _ in {1..50}; do
  if [[ -S /tmp/.X11-unix/X99 ]]; then break; fi
  sleep .1
done
fluxbox > salida/visual/fluxbox.log 2>&1 &
x11vnc -display :99 -nopw -forever -shared -rfbport 5900 -listen 0.0.0.0 \
  -o salida/visual/vnc.log -bg
echo 'SUMO-GUI disponible por VNC en localhost:5902 (puerto del anfitrión).'
echo 'Abre Remmina u otro visor VNC. Sigue los pasos de la terminal.'
export PATH="$PWD/scripts/gui_bin:$PATH"
python3 scripts/demo_validacion.py "$@"
