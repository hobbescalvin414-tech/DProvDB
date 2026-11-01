#!/usr/bin/env bash
# Compile once before dispatch; each invocation owns one output directory.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
DATASET=${1:?dataset}
OUT=${2:?output directory, repository-relative}
MODE=${3:-formal}
case "$DATASET" in bank|credit|shoppers|diabetes|covertype) ;; *) exit 2;; esac
case "$MODE" in smoke|formal) ;; *) exit 2;; esac
[[ "$OUT" != /* && "$OUT" != *..* && ! -e "$OUT" ]] || { echo 'Output must be new and repository-relative'; exit 2; }
mkdir -p "$(dirname "$OUT")"
CP=$(cat .runtime/five-datasets/classpath.txt)
# Read only this project container's DB environment, never a host/global credential.
DPROVDB_DB_USER=$(docker exec dprovdb-repro-db printenv POSTGRES_USER)
DPROVDB_DB_PASSWORD=$(docker exec dprovdb-repro-db printenv POSTGRES_PASSWORD)
export DPROVDB_DB_USER DPROVDB_DB_PASSWORD
STARTED=$(date -u +%FT%TZ)
STATUS=0
# 2 concurrent containers max: 2 x 2 GiB plus existing 1 GiB DB, on 8 GiB Docker.
docker run --rm --name "dprovdb-five-$DATASET-$MODE" --cpus=2 --memory=2g \
 --network container:dprovdb-repro-db -e DPROVDB_PROFILE=paper -e DPROVDB_DB_USER -e DPROVDB_DB_PASSWORD \
 -v "$ROOT:/workspace" -v "$ROOT/.runtime/m2:/root/.m2:ro" \
 -v "$ROOT/.runtime/coursier:/root/.cache/coursier:ro" \
 dprovdb-repro:java11 java -Xmx1200m -cp "$CP" edu.Experiments.FiveDatasets "$DATASET" "$OUT" "$MODE" \
 > "$OUT.log" 2>&1 || STATUS=$?
printf 'dataset\tmode\tstarted_utc\tfinished_utc\texit_code\n%s\t%s\t%s\t%s\t%s\n' \
 "$DATASET" "$MODE" "$STARTED" "$(date -u +%FT%TZ)" "$STATUS" > "$OUT.timing.tsv"
exit "$STATUS"
