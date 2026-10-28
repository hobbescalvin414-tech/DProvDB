#!/usr/bin/env bash
# Fresh-clone setup. Uses only this repository and dedicated Docker resources.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if docker container inspect dprovdb-repro-db >/dev/null 2>&1; then
  echo 'Dedicated database already exists. Refusing to recreate or overwrite it.' >&2
  exit 1
fi
if docker volume inspect dprovdb-repro-pgdata >/dev/null 2>&1; then
  echo 'Dedicated database volume already exists. Refusing to overwrite it.' >&2
  exit 1
fi
mkdir -p .runtime/datasets .runtime/logs
git submodule update --init --recursive
docker build -t dprovdb-repro:java11 reproduction
curl -fL --retry 3 https://archive.ics.uci.edu/static/public/2/adult.zip -o .runtime/datasets/uci-adult.zip
bash reproduction/container.sh python3 reproduction/prepare-adult.py
git clone https://github.com/gregrahn/tpch-kit.git .runtime/tpch-kit
git -C .runtime/tpch-kit checkout 852ad0a5ee31ebefeed884cea4188781dd9613a3
bash reproduction/container.sh bash -c 'cd .runtime/tpch-kit/dbgen && make -j1 MACHINE=LINUX DATABASE=POSTGRESQL && ./dbgen -s 1'
docker run -d --name dprovdb-repro-db --cpus=1 --memory=1g --restart=no \
  -e POSTGRES_USER=link -e POSTGRES_PASSWORD=12345 -e POSTGRES_DB=adult \
  -v dprovdb-repro-pgdata:/var/lib/postgresql/data -v "$ROOT:/workspace:ro" \
  postgres:16.1-alpine@sha256:17eb369d9330fe7fbdb2f705418c18823d66322584c77c2b43cc0e1851d01de7
trap 'docker stop dprovdb-repro-db >/dev/null' EXIT
ready=false
for attempt in {1..30}; do
  if docker exec dprovdb-repro-db pg_isready -U link -d adult; then ready=true; break; fi
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Database did not become ready' >&2; exit 1; }
docker exec dprovdb-repro-db psql -v ON_ERROR_STOP=1 -U link -d adult -f /workspace/data/adult.ddl
docker exec dprovdb-repro-db psql -v ON_ERROR_STOP=1 -U link -d adult -c "\copy adult FROM '/workspace/.runtime/datasets/adult-complete.csv' CSV"
docker exec dprovdb-repro-db createdb -U link adult_upstream
docker exec dprovdb-repro-db psql -v ON_ERROR_STOP=1 -U link -d adult_upstream -f /workspace/data/adult.ddl
docker exec dprovdb-repro-db psql -v ON_ERROR_STOP=1 -U link -d adult_upstream -c "\copy adult FROM '/workspace/data/adult.data' CSV"
docker exec dprovdb-repro-db createdb -U link tpch
docker exec dprovdb-repro-db psql -v ON_ERROR_STOP=1 -U link -d tpch -f /workspace/.runtime/tpch-kit/dbgen/dss.ddl
bash reproduction/load-tpch.sh
bash reproduction/build.sh
