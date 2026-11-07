#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
sdk="${ANDROID_HOME:?Configure ANDROID_HOME with the Android SDK}"
tools="$sdk/build-tools/35.0.0"
platform="$sdk/platforms/android-35/android.jar"
output="${1:?Provide an absolute path for the APK}"
signing_key="${HUE_ANDROID_KEYSTORE:?Provide a local Android test keystore}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

mkdir -p "$work/classes" "$work/dex"
"$tools/aapt2" compile --dir res -o "$work/res.zip"
"$tools/aapt2" link -I "$platform" --manifest AndroidManifest.xml \
    -o "$work/unsigned.apk" "$work/res.zip"
javac --release 8 -encoding UTF-8 -classpath "$platform" -d "$work/classes" \
    src/ch/huelab/mobile/*.java
jar cf "$work/classes.jar" -C "$work/classes" .
"$tools/d8" --min-api 26 --lib "$platform" --output "$work/dex" "$work/classes.jar"
(
    cd "$work/dex"
    zip -q "$work/unsigned.apk" classes.dex
)
"$tools/zipalign" -p -f 4 "$work/unsigned.apk" "$work/aligned.apk"
"$tools/apksigner" sign --ks "$signing_key" --ks-key-alias androiddebugkey \
    --ks-pass pass:android --key-pass pass:android --out "$output" "$work/aligned.apk"
"$tools/apksigner" verify --verbose "$output"
"$tools/aapt2" dump badging "$output" | sed -n '1,9p'
