#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/.runtime/m2" "$ROOT/.runtime/sbt" "$ROOT/.runtime/ivy2" "$ROOT/.runtime/coursier"
network_args=()
if [[ "${DPROVDB_WITH_DB:-0}" == 1 ]]; then
  network_args=(--network container:dprovdb-repro-db)
fi
exec docker run --rm --cpus=2 --memory=4g ${network_args[@]+"${network_args[@]}"} \
  -e DPROVDB_PROFILE -e DPROVDB_OUTPUT_DIR -e DPROVDB_RUNS -e DPROVDB_LOG_LEVEL \
  -v "$ROOT:/workspace" -v "$ROOT/.runtime/m2:/root/.m2" \
  -v "$ROOT/.runtime/sbt:/root/.sbt" -v "$ROOT/.runtime/ivy2:/root/.ivy2" \
  -v "$ROOT/.runtime/coursier:/root/.cache/coursier" \
  dprovdb-repro:java11 "$@"
