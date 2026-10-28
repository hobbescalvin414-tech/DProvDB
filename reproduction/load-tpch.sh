#!/usr/bin/env bash
# Load only into the task-owned Docker database. Refuse nonempty tables.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for table in region nation supplier customer part partsupp orders lineitem; do
  test -s "$ROOT/.runtime/tpch-kit/dbgen/$table.tbl"
done
for table in region nation supplier customer part partsupp orders lineitem; do
  rows=$(docker exec dprovdb-repro-db psql -U link -d tpch -Atc "SELECT count(*) FROM $table")
  if [[ "$rows" != 0 ]]; then
    echo "Refusing to append to nonempty table: $table ($rows rows)" >&2
    exit 1
  fi
  LC_ALL=C sed 's/|$//' "$ROOT/.runtime/tpch-kit/dbgen/$table.tbl" | \
    docker exec -i dprovdb-repro-db psql -v ON_ERROR_STOP=1 -U link -d tpch \
      -c "COPY $table FROM STDIN WITH (FORMAT csv, DELIMITER '|')"
done
docker exec dprovdb-repro-db psql -v ON_ERROR_STOP=1 -U link -d tpch -c ANALYZE
