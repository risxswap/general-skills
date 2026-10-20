#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
version=${VERSION:-$(cat "$root/VERSION")}
output=${OUTPUT:-"$root/dist"}
targets=${TARGETS:-darwin/arm64}
python3 "$root/scripts/validate_skills.py"
# package.sh owns the default dist directory; remove the previous release so
# repeated local builds do not fail the Go packager's no-overwrite guard.
if [ "$output" = "$root/dist" ]; then
	rm -rf -- "$output"
fi
cd "$root/tools"
go run ./cmd/general-skills package --root "$root" --output "$output" --version "$version" --targets "$targets"
