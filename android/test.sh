#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
# JSON implementation for the host JVM only; Android supplies org.json in the APK.
curl --fail --silent --show-error --max-time 60 -o "$work/json.jar" \
  https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar
printf '%s  %s\n' '3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed' "$work/json.jar" > "$work/checksum"
# Dependency integrity check (host tests only).
sha256sum --check --status "$work/checksum"
javac --release 8 -encoding UTF-8 -cp "$work/json.jar" -d "$work/classes" \
  src/ch/huelab/mobile/AlarmSync.java src/ch/huelab/mobile/LocalServer.java \
  tests/android/app/*.java tests/android/content/*.java tests/ch/huelab/mobile/*.java
java -cp "$work/classes:$work/json.jar" ch.huelab.mobile.ManualAlarmTest
