#!/usr/bin/env bash
# Demostración en un contenedor separado; el VNC solo se publica en localhost.
set -euo pipefail
cd "$(dirname "$0")/.."
docker_args=(--rm --name reto-ambulancias-gui --user "$(id -u):$(id -g)")
if [[ "${1:-}" != "--automatico" ]]; then docker_args+=(-it); fi
exec docker run "${docker_args[@]}" \
  -e HOME=/tmp -e DISPLAY=:99 -e SUMO_HOME=/usr/share/sumo \
  -e LIBGL_ALWAYS_SOFTWARE=1 \
  -p "127.0.0.1:${RETO_VNC_PORT:-5902}:5900" \
  -v "$PWD:/work" -w /work --entrypoint bash \
  "${SUMO_IMAGE:-van3twin:jammy}" scripts/iniciar_gui.sh "$@"
