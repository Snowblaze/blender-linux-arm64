#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
recipe_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${1:-$recipe_dir}" && pwd)"
source "$recipe_dir/build-settings.sh"
release_dir="$recipe_dir/release"
folder="blender-$blender_version-linux-arm64"
# Name the actual build OS, not Debian/Pi 5 for artifacts built on Ubuntu hosts.
os_id="$(. /etc/os-release; printf '%s%s' "$ID" "$VERSION_ID")"
[[ "$os_id" =~ ^[a-zA-Z0-9.]+$ ]] || { echo 'Invalid OS label.' >&2; exit 1; }
revision="${BLENDER_PACKAGE_REVISION:-1}"
[[ "$revision" =~ ^[1-9][0-9]*$ ]] || { echo "Invalid package revision." >&2; exit 1; }
binary_name="blender-linux-arm64_${blender_version}-${revision}+${os_id}_arm64.deb"
source_name="blender-$blender_version-source.tar.xz"
[[ -x "$install_dir/blender" && -f "$project_dir/source/CMakeLists.txt" && -f "$project_dir/logs/dependency-sources.tsv" ]] || {
    echo 'Prepare sources and build first. Set BLENDER_INSTALL_DIR for a custom installation.' >&2
    exit 1
}
mkdir -p "$release_dir"
staging="$(mktemp -d "$release_dir/.staging.XXXXXX")"
trap 'rm -rf -- "$staging"' EXIT
cp -a "$install_dir" "$staging/$folder"
for file in README.md fetch-dependency-source.py LICENSE; do
    cp "$recipe_dir/$file" "$staging/$folder/"
done
cp "$project_dir/logs/dependency-sources.tsv" "$staging/dependency-sources.tsv"
cp "$project_dir/logs/build-info.json" "$staging/BUILD-INFO.json"
cp "$staging/dependency-sources.tsv" "$staging/BUILD-INFO.json" "$staging/$folder/"
python3 "$recipe_dir/package-deb.py" --payload "$staging/$folder" \
    --output "$release_dir" --version "$blender_version" --os-label "$os_id" \
    --log "$project_dir/logs/package-dependencies.log"
cp "$release_dir/BUILD-INFO.json" "$staging/BUILD-INFO.json"
recipe_files=(README.md LICENSE build-blender.sh build-settings.sh \
    prepare-source.sh prepare-source.py generate-dependency-manifest.cmake package-release.sh package-deb.py blender-launcher.py \
    fetch-dependency-source.py verify-build.py verify-ui.py config .github/workflows/manual-build.yml)
tar -cJf "$release_dir/$source_name" \
    --exclude=.git --exclude=source/lib --exclude=source/tests/data \
    -C "$project_dir" source -C "$recipe_dir" "${recipe_files[@]}" \
    -C "$staging" dependency-sources.tsv BUILD-INFO.json
cp "$staging/BUILD-INFO.json" "$release_dir/BUILD-INFO.json"
cd "$release_dir"
sha256sum "$binary_name" "$source_name" BUILD-INFO.json > SHA256SUMS
for asset in "$binary_name" "$source_name"; do
    [[ "$(stat -c %s "$asset")" -lt 2147483648 ]] || {
        echo "Asset exceeds GitHub's 2 GiB limit: $asset" >&2
        exit 1
    }
done
printf 'Release assets: %s\n' "$release_dir"
