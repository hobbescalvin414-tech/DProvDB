#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# A concurrently dispatched batch owns its output; the serial coordinator joins
# it instead of running the same experiment twice. Claims are local to one run.
if [[ -n "${DPROVDB_OUTPUT_DIR:-}" && $# == 1 && "$1" == runMain* ]]; then
  key=$(printf '%s' "$1" | tr ' /' '__')
  claim="$ROOT/$DPROVDB_OUTPUT_DIR/../external/$key"
  if [[ -f "$claim.claim" ]]; then
    while [[ ! -f "$claim.status" ]]; do sleep 2; done
    cat "$claim.log"
    exit "$(cat "$claim.status")"
  fi
fi
exec bash "$ROOT/reproduction/container.sh" java \
  -Dsbt.override.build.repos=true \
  -Dsbt.repository.config=/workspace/reproduction/sbt-repositories \
  -Dsbt.supershell=false -Dsbt.server.autostart=false \
  -jar /opt/sbt/sbt-launch.jar "$@"
