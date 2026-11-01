#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
mkdir -p .runtime/five-datasets
# Existing reproduction image and Chorus artifact; see reproduction/build.sh for first build.
DPROVDB_PROFILE=paper bash reproduction/sbt.sh compile 'testOnly edu.DProvDB.Utils.RandomBasisTest' 'export Runtime / fullClasspath' > .runtime/five-datasets/build.log 2>&1
python3 - <<'PY'
from pathlib import Path
p=Path('.runtime/five-datasets')
lines=(p/'build.log').read_text().splitlines()
(p/'classpath.txt').write_text(next(s for s in lines if s.startswith('/workspace/target/'))+'\n')
PY
