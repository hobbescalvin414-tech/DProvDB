#!/usr/bin/env bash
# Run a claimed batch with direct Java, avoiding concurrent sbt target mutation.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT=reproduction/results/paper-2026-10-28
DATASET=$1
TABLE=$2
FLAGS=$3
COMMAND="runMain edu.Experiments.Experiment $DATASET RRQ $TABLE $FLAGS"
KEY=$(printf '%s' "$COMMAND" | tr ' /' '__')
BASE="$OUT/external/$KEY"
test -f "$BASE.claim"
CP=$(cat .runtime/runtime-classpath.txt)
export DPROVDB_WITH_DB=1 DPROVDB_PROFILE=paper DPROVDB_RUNS=4 DPROVDB_LOG_LEVEL=info DPROVDB_OUTPUT_DIR="$OUT/raw"
STARTED=$(date -u +%FT%TZ)
STATUS=0
bash reproduction/container.sh java -Xmx1500m -cp "$CP" edu.Experiments.Experiment "$DATASET" RRQ "$TABLE" "$FLAGS" > "$BASE.log" 2>&1 || STATUS=$?
printf '%s\tRRQ\t%s\t%s\t%s\t%s\n' "$DATASET" "$FLAGS" "$STARTED" "$(date -u +%FT%TZ)" "$STATUS" > "$BASE.timing.tsv"
printf '%s\n' "$STATUS" > "$BASE.status"
exit "$STATUS"
