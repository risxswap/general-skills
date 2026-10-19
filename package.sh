#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
version=${VERSION:-$(cat "$root/VERSION")}
output=${OUTPUT:-"$root/dist/$version"}
targets=${TARGETS:-darwin/amd64,darwin/arm64,windows/amd64,windows/arm64,linux/amd64,linux/arm64}
python3 "$root/scripts/validate_skills.py"
cd "$root/tools"
go run ./cmd/general-skills package --root "$root" --output "$output" --version "$version" --targets "$targets"
