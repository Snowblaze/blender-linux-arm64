#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn the staged portable installation into an ARM64 Debian package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

PACKAGE = 'blender-linux-arm64'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--os-label', required=True)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    revision = os.environ.get('BLENDER_PACKAGE_REVISION', '1')
    if not re.fullmatch(r'[1-9][0-9]*', revision):
        parser.error('BLENDER_PACKAGE_REVISION must be a positive integer.')
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.version) or not re.fullmatch(r'[a-zA-Z0-9.]+', args.os_label):
        parser.error('Invalid version or OS label.')
    if subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip() != 'arm64':
        parser.error('Build this package on native Debian/Ubuntu ARM64.')
    for command in ['dpkg-deb', 'dpkg-shlibdeps', 'readelf']:
        if not shutil.which(command):
            parser.error(f'Missing {command}; install dpkg-dev and binutils.')
    args.output.mkdir(parents=True, exist_ok=True)
    package_version = f'{args.version}-{revision}+{args.os_label}'
    maintainer = os.environ.get('BLENDER_PACKAGE_MAINTAINER', 'Snowblaze <Snowblaze@users.noreply.github.com>')
    if '\n' in maintainer or '\r' in maintainer or not re.fullmatch(r'.+ <[^<>\s]+@[^<>\s]+>', maintainer):
        parser.error('Invalid BLENDER_PACKAGE_MAINTAINER.')
    work = args.payload.resolve().parent/'deb-work'
    debian = work/'debian'
    package_root = debian/PACKAGE
    payload = package_root/'usr/lib'/PACKAGE
    payload.parent.mkdir(parents=True)
    shutil.move(str(args.payload), str(payload))
    # This recipe builds CPU-only Cycles. Official OIDN bundles also ship optional
    # GPU plugins; omitting those avoids requiring an NVIDIA/HIP/SYCL driver.
    excluded = []
    for backend in ['cuda', 'hip', 'sycl']:
        for plugin in (payload/'lib').glob(f'libOpenImageDenoise_device_{backend}.so*'):
            excluded.append(plugin.name)
            plugin.unlink()
    metadata = payload/'BUILD-INFO.json'
    info = json.loads(metadata.read_text())
    info.update(package_name=PACKAGE, package_version=package_version,
                package_build_os=args.os_label, omitted_optional_oidn_plugins=excluded)
    metadata.write_text(json.dumps(info, indent=2)+'\n')
    # Keep the separately uploaded record identical to the package's metadata.
    shutil.copy2(metadata, args.output/'BUILD-INFO.json')
    control_dir = package_root/'DEBIAN'
    control_dir.mkdir()
    # A source control file lets dpkg-shlibdeps identify this package's private libraries.
    (debian/'control').write_text(f'''Source: {PACKAGE}
Section: graphics
Priority: optional
Maintainer: {maintainer}

Package: {PACKAGE}
Architecture: arm64
Description: Unofficial Blender for Linux ARM64
''')
    (control_dir/'control').write_text(f'Package: {PACKAGE}\nVersion: {package_version}\nArchitecture: arm64\nMaintainer: {maintainer}\nDescription: Unofficial Blender for Linux ARM64\n')
    bin_dir = package_root/'usr/bin'
    bin_dir.mkdir(parents=True)
    launcher = payload/'blender-launcher.py'
    shutil.copy2(Path(__file__).resolve().parent/'blender-launcher.py', launcher)
    launcher.chmod(0o755)
    (bin_dir/'blender').symlink_to(f'../lib/{PACKAGE}/blender-launcher.py')
    if (payload/'blender-thumbnailer').exists():
        (bin_dir/'blender-thumbnailer').symlink_to(f'../lib/{PACKAGE}/blender-thumbnailer')
    applications = package_root/'usr/share/applications'
    applications.mkdir(parents=True)
    (applications/f'{PACKAGE}.desktop').write_text(f'''[Desktop Entry]
Name=Blender (ARM64 Community Build)
Comment=3D modeling, animation and rendering with automatic graphics selection
Exec=/usr/bin/blender %f
TryExec=/usr/bin/blender
Icon={PACKAGE}
Terminal=false
Type=Application
Categories=Graphics;3DGraphics;
MimeType=application/x-blender;
StartupWMClass=Blender
''')
    icons = package_root/'usr/share/icons/hicolor/scalable/apps'
    icons.mkdir(parents=True)
    shutil.copy2(payload/'blender.svg', icons/f'{PACKAGE}.svg')
    mime = package_root/'usr/share/mime/packages'
    mime.mkdir(parents=True)
    (mime/f'{PACKAGE}.xml').write_text('''<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-blender">
    <comment>Blender scene</comment>
    <glob pattern="*.blend"/>
    <magic priority="50"><match type="string" offset="0" value="BLENDER"/></magic>
  </mime-type>
</mime-info>
''')
    documentation = package_root/'usr/share/doc'/PACKAGE
    documentation.mkdir(parents=True)
    for filename in ['README.md', 'BUILD-INFO.json', 'dependency-sources.tsv']:
        shutil.copy2(payload/filename, documentation/filename)
    (documentation/'copyright').write_text(
        'Blender: Copyright Blender Foundation and Blender contributors.\n'
        'This unofficial binary distribution is licensed GPL-3.0-or-later.\n'
        f'Third-party copyright and license notices are preserved in /usr/lib/{PACKAGE}/license/.\n'
        'Corresponding source and dependency-source access are described in README.md and BUILD-INFO.json.\n\n'
        +(payload/'LICENSE').read_text())
    if (payload/'blender.1').exists():
        man = package_root/'usr/share/man/man1'
        man.mkdir(parents=True)
        import gzip
        with (payload/'blender.1').open('rb') as source, gzip.open(man/'blender.1.gz', 'wb') as target:
            shutil.copyfileobj(source, target)
    elfs = []
    for path in sorted(payload.rglob('*')):
        if path.is_file() and not path.is_symlink():
            with path.open('rb') as file:
                if file.read(4) == b'\x7fELF':
                    elfs.append(path)
    if not elfs:
        parser.error('The staged installation contains no ELF binaries.')
    header = subprocess.check_output(['readelf', '-h', str(payload/'blender')], text=True)
    if not re.search(r'Machine:\s+AArch64', header):
        parser.error('The Blender executable is not ARM64.')
    private_dirs = sorted({str(path.parent) for path in elfs})
    command = ['dpkg-shlibdeps', '-O', f'-S{package_root}', f'-x{PACKAGE}']
    command += [f'-l{directory}' for directory in private_dirs]
    command += [str(path) for path in elfs]
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open('w') as log:
        result = subprocess.run(command, cwd=work, text=True, stdout=subprocess.PIPE, stderr=log)
    if result.returncode:
        raise SystemExit(f'Failed to resolve package dependencies; see {args.log}.')
    match = re.search(r'^shlibs:Depends=(.+)$', result.stdout, re.M)
    if not match:
        raise SystemExit('dpkg-shlibdeps returned no system library dependencies.')
    # Blender also loads graphics/windowing/audio libraries dynamically, so they
    # cannot all be discovered from ELF NEEDED entries alone.
    runtime = ['python3', 'libgl1', 'libegl1', 'libgl1-mesa-dri', 'libegl-mesa0', 'libvulkan1',
               'libx11-6', 'libxi6', 'libxfixes3', 'libxrender1', 'libxrandr2',
               'libxxf86vm1', 'libxcursor1', 'libwayland-client0', 'libwayland-cursor0',
               'libwayland-egl1', 'libxkbcommon0', 'libdecor-0-0', 'libdbus-1-3',
               'libpulse0', 'libasound2t64', 'libjack-jackd2-0']
    dependencies = match[1]+', '+', '.join(runtime)
    # Remove group/world-write bits inherited from the development installation.
    for path in package_root.rglob('*'):
        if not path.is_symlink():
            path.chmod(stat.S_IMODE(path.stat().st_mode) & ~0o022)
    size = sum(path.stat().st_size for path in package_root.rglob('*') if path.is_file() and not path.is_symlink())
    (control_dir/'control').write_text(f'''Package: {PACKAGE}
Version: {package_version}
Architecture: arm64
Section: graphics
Priority: optional
Maintainer: {maintainer}
Homepage: https://github.com/Snowblaze/blender-linux-arm64
Installed-Size: {(size+1023)//1024}
Depends: {dependencies}
Recommends: desktop-file-utils, hicolor-icon-theme, shared-mime-info
Provides: blender (= {args.version})
Conflicts: blender
Description: Unofficial stable Blender build for Linux ARM64
 CPU rendering and automatic hardware/software graphics with desktop integration.
 Built for {args.os_label}; see the included README for hardware requirements.
''')
    with (control_dir/'md5sums').open('w') as hashes:
        for path in sorted((package_root/'usr').rglob('*')):
            if path.is_file() and not path.is_symlink():
                with path.open('rb') as file:
                    digest = hashlib.file_digest(file, 'md5').hexdigest()
                hashes.write(f'{digest}  {path.relative_to(package_root)}\n')
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output/f'{PACKAGE}_{package_version}_arm64.deb'
    subprocess.run(['dpkg-deb', '--root-owner-group', '-Zxz', '-z3', '--build', str(package_root), str(output)], check=True)
    print(f'Debian installer: {output}', flush=True)

if __name__ == '__main__':
    main()
