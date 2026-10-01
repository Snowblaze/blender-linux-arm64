#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
# Locally extracted tooling is optional; hosted runners use system tools.
if [[ -d tools/usr/bin ]]; then export PATH="$project_dir/tools/usr/bin:$PATH"; fi
for tool in git python3 cmake; do command -v "$tool" >/dev/null; done
git lfs version >/dev/null
python3 prepare-source.py
cmake -DSOURCE_DIR="$project_dir/source" -DOUTPUT_FILE="$project_dir/logs/dependency-sources.tsv" \
  -P generate-dependency-manifest.cmake
python3 prepare-source.py --check-dependencies
