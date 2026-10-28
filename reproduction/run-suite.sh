#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${1:-reproduction/results/paper-2026-10-28}"
if [[ -e "$OUT" ]]; then
  echo "Refusing to overwrite existing results: $OUT" >&2
  exit 1
fi
mkdir -p "$OUT/raw" "$OUT/logs"
export DPROVDB_WITH_DB=1 DPROVDB_PROFILE=paper DPROVDB_RUNS=4 DPROVDB_LOG_LEVEL=info
export DPROVDB_OUTPUT_DIR="$OUT/raw"
docker start dprovdb-repro-db >/dev/null
trap 'docker stop dprovdb-repro-db >/dev/null' EXIT
printf 'dataset\ttask\tgroup\tstarted_utc\tfinished_utc\texit_code\n' > "$OUT/timing.tsv"
for dataset in adult tpch; do
  table=adult
  [[ "$dataset" == tpch ]] && table=orders
  for spec in EQW:TFFFFF RRQ:TFFFFF RRQ:FTFFFF RRQ:FFTFFF RRQ:FFFTFF RRQ:FFFFTF; do
    task=${spec%%:*}
    flags=${spec##*:}
    log="$OUT/logs/${dataset}_${task}_${flags}.log"
    started=$(date -u +%FT%TZ)
    echo "Starting $dataset $task $flags at $started"
    status=0
    bash reproduction/sbt.sh "runMain edu.Experiments.Experiment $dataset $task $table $flags" > "$log" 2>&1 || status=$?
    if rg -q '^\[error\]' "$log"; then status=1; fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$dataset" "$task" "$flags" "$started" "$(date -u +%FT%TZ)" "$status" >> "$OUT/timing.tsv"
    [[ "$status" == 0 ]] || { tail -40 "$log"; exit "$status"; }
    gzip "$log"
    echo "Completed $dataset $task $flags"
  done
done
log="$OUT/logs/adult_RRQ_FFFFFT.log"
started=$(date -u +%FT%TZ)
status=0
bash reproduction/sbt.sh 'runMain edu.Experiments.Experiment adult RRQ adult FFFFFT' > "$log" 2>&1 || status=$?
if rg -q '^\[error\]' "$log"; then status=1; fi
printf 'adult\tRRQ\tFFFFFT\t%s\t%s\t%s\n' "$started" "$(date -u +%FT%TZ)" "$status" >> "$OUT/timing.tsv"
[[ "$status" == 0 ]] || { tail -40 "$log"; exit "$status"; }
gzip "$log"
echo 'Suite finished successfully.'
