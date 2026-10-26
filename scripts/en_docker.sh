#!/usr/bin/env bash
# No arranca ni modifica los contenedores de otros talleres.
set -euo pipefail
cd "$(dirname "$0")/.."
exec docker run --rm --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e SUMO_HOME=/usr/share/sumo -e MPLCONFIGDIR=/tmp/matplotlib \
  -v "$PWD:/work" -w /work --entrypoint /bin/bash \
  "${SUMO_IMAGE:-van3twin:jammy}" -c 'exec "$@"' bash "$@"
