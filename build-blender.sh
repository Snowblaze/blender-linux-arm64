#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
source "$project_dir/build-settings.sh"
# Prefer standard system tools; locally extracted tools are optional.
if [[ -d "$project_dir/tools/usr/bin" ]]; then
  export PATH="$project_dir/tools/usr/bin:$PATH"
fi
if [[ -d "$project_dir/tools/usr/lib/aarch64-linux-gnu" ]]; then
  export LD_LIBRARY_PATH="$project_dir/tools/usr/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
[[ "$(uname -m)" == aarch64 ]] || { echo 'This recipe targets native Linux ARM64.' >&2; exit 1; }
for tool in cmake ninja cc c++; do
  command -v "$tool" >/dev/null || { echo "Missing build tool: $tool" >&2; exit 1; }
done
[[ -f source/CMakeLists.txt && -d source/lib/linux_arm64 ]] || {
  echo 'Run ./prepare-source.sh first.' >&2
  exit 1
}
mkdir -p logs
cmake -S source -B "$build_dir" -G Ninja \
  -C config/windows-arm64-features.cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DNINJA_MAX_NUM_PARALLEL_COMPILE_JOBS=4 \
  -DNINJA_MAX_NUM_PARALLEL_COMPILE_HEAVY_JOBS=3 \
  -DNINJA_MAX_NUM_PARALLEL_LINK_JOBS=1 \
  -DCMAKE_INSTALL_PREFIX="$install_dir" \
  -DWITH_INSTALL_PORTABLE=ON \
  -DWITH_CYCLES_NATIVE_ONLY="${BLENDER_NATIVE_ONLY:-ON}" \
  -DWITH_CPU_CHECK=OFF \
  2>&1 | tee logs/configure.log
cmake --build "$build_dir" --parallel "${BLENDER_BUILD_JOBS:-4}" 2>&1 | tee -a logs/build.log
cmake --install "$build_dir" 2>&1 | tee logs/install.log
"$install_dir/blender" --version | tee logs/version.log
python3 - "$metadata_file" "${BLENDER_NATIVE_ONLY:-ON}" "$build_dir" <<'PYINFO'
import json, platform, subprocess, sys
from pathlib import Path
path = Path(sys.argv[1])
info = json.loads(path.read_text())
cache = Path(sys.argv[3], 'CMakeCache.txt').read_text().splitlines()
compiler = next(line.split('=', 1)[1] for line in cache if line.startswith('CMAKE_C_COMPILER:'))
info.update(build_os=platform.freedesktop_os_release(), build_machine=platform.machine(),
            cycles_native_only=sys.argv[2], compiler=subprocess.check_output([compiler, '--version'], text=True).splitlines()[0])
try:
    info['recipe_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
except subprocess.CalledProcessError:
    info['recipe_commit'] = None
path.write_text(json.dumps(info, indent=2)+'\n')
PYINFO
