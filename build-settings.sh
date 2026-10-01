#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Shared settings. Source this after defining project_dir.
metadata_file="$project_dir/logs/build-info.json"
if [[ -f "$metadata_file" ]]; then
  mapfile -t resolved < <(python3 - "$metadata_file" <<'PY'
import json, sys
info = json.load(open(sys.argv[1]))
print(info['version'])
print(info['source_commit'])
print(info['dependency_commit'])
PY
)
  blender_version="${resolved[0]}"
else
  blender_version="${BLENDER_VERSION:-}"
fi
[[ "$blender_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo 'Run ./prepare-source.sh to select a stable Blender version first.' >&2
  return 1
}
if [[ -n "${BLENDER_VERSION:-}" && "$BLENDER_VERSION" != "$blender_version" ]]; then
  echo 'Requested version differs from the prepared source. Run ./prepare-source.sh first.' >&2
  return 1
fi
install_dir="${BLENDER_INSTALL_DIR:-$HOME/.local/opt/blender-$blender_version-linux-arm64}"
build_dir="${BLENDER_BUILD_DIR:-$project_dir/build/$blender_version}"
