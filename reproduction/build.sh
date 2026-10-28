#!/usr/bin/env bash
# Compile dependencies and project only; does not execute experiments.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p .runtime/logs project
printf 'sbt.version=1.10.7\n' > project/build.properties
bash reproduction/container.sh bash -lc 'cd chorus && mvn -B -Dmaven.test.skip=true install'
# Maven downloads this transitive POM without its JAR. Complete the local
# artifact so Coursier can resolve it without mixing repository locations.
ARTIFACT=.runtime/m2/repository/org/slf4j/slf4j-api/1.7.13/slf4j-api-1.7.13.jar
if [[ ! -s "$ARTIFACT" ]]; then
  mkdir -p "$(dirname "$ARTIFACT")"
  curl -fL --retry 3 https://repo.maven.apache.org/maven2/org/slf4j/slf4j-api/1.7.13/slf4j-api-1.7.13.jar -o "$ARTIFACT"
fi
bash reproduction/sbt.sh compile 'show Compile / discoveredMainClasses'
