#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve stable upstream tags and matching ARM64 libraries; record exact commits."""
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SOURCE_URL = 'https://projects.blender.org/blender/blender.git'
LIBRARY_URL = 'https://projects.blender.org/blender/lib-linux_arm64.git'

def git(*args, cwd=None, capture=False):
    return subprocess.run(['git', *args], cwd=cwd, check=True,
                          text=True, stdout=subprocess.PIPE if capture else None).stdout

def stable_versions(refs):
    versions = set()
    for line in refs.splitlines():
        match = re.search(r'\trefs/tags/v(\d+)\.(\d+)\.(\d+)$', line)
        if match:
            versions.add(tuple(map(int, match.groups())))
    return sorted(versions)

def checkout(directory, url, ref):
    if directory.exists() and not (directory/'.git').is_dir():
        raise SystemExit(f'{directory} is not a Git checkout; use a fresh checkout to prepare another version.')
    if not directory.exists():
        directory.mkdir(parents=True)
        git('init', str(directory))
        git('remote', 'add', 'origin', url, cwd=directory)
        git('lfs', 'install', '--local', cwd=directory)
    else:
        # Never discard user changes to upstream source.
        git('diff', '--exit-code', cwd=directory)
        git('diff', '--cached', '--exit-code', cwd=directory)
    git('fetch', '--depth', '1', 'origin', ref, cwd=directory)
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE='1')
    subprocess.run(['git', 'checkout', '--detach', 'FETCH_HEAD'], cwd=directory, env=env, check=True)
    return git('rev-parse', 'HEAD', cwd=directory, capture=True).strip()

def check_dependencies():
    rows = list(csv.DictReader((ROOT/'logs/dependency-sources.tsv').open(), delimiter='\t'))
    versions = {row['name']: row['version'] for row in rows if row['version']}
    deps = (ROOT/'source/lib/linux_arm64/deps.md').read_text()
    mismatches = []
    for name, version in re.findall(r'^\| `([^`]+)` \| `([^`]+)`', deps, re.M):
        if name in versions and versions[name] != version:
            mismatches.append(f'{name}: source needs {versions[name]}, libraries list {version}')
    if mismatches:
        print('Dependency version differences (CMake and verification will check compatibility):\n'+'\n'.join(mismatches), flush=True)
        (ROOT/'logs/dependency-version-differences.txt').write_text('\n'.join(mismatches)+'\n')
    if not re.search(r'^\| `', deps, re.M):
        raise SystemExit('Cannot validate the ARM64 dependency manifest.')
    if not mismatches:
        print('ARM64 dependency versions match the source manifest.', flush=True)

def main():
    if '--check-dependencies' in sys.argv:
        check_dependencies()
        return
    requested = os.environ.get('BLENDER_VERSION', '').strip().removeprefix('v')
    archive_info = None
    if (ROOT/'source').is_dir() and not (ROOT/'source/.git').exists() and (ROOT/'BUILD-INFO.json').exists():
        archive_info = json.loads((ROOT/'BUILD-INFO.json').read_text())
        if requested and requested != archive_info['version']:
            raise SystemExit('Source archive contains a different version; use a fresh recipe checkout.')
        requested = archive_info['version']
    if requested and not re.fullmatch(r'\d+\.\d+\.\d+', requested):
        raise SystemExit('BLENDER_VERSION must be a stable version such as 5.2.2.')
    if not requested:
        versions = stable_versions(git('ls-remote', '--tags', SOURCE_URL, capture=True))
        if not versions:
            raise SystemExit('No stable Blender tags found.')
        requested = '.'.join(map(str, versions[-1]))
    source = ROOT/'source'
    if archive_info:
        source_commit = archive_info['source_commit']
    else:
        source_commit = checkout(source, SOURCE_URL, 'refs/tags/v'+requested)
        git('lfs', 'pull', '--include=release/**,assets/**,scripts/**', '--exclude=', cwd=source)
    header = (source/'source/blender/blenkernel/BKE_blender_version.h').read_text()
    combined = int(re.search(r'^#define BLENDER_VERSION\s+(\d+)', header, re.M)[1])
    patch = int(re.search(r'^#define BLENDER_VERSION_PATCH\s+(\d+)', header, re.M)[1])
    cycle = re.search(r'^#define BLENDER_VERSION_CYCLE\s+(\w+)', header, re.M)[1]
    actual = f'{combined//100}.{combined%100}.{patch}'
    if actual != requested or cycle != 'release':
        raise SystemExit(f'Tag is not the requested stable release: {actual}, {cycle}')
    library_ref = os.environ.get('BLENDER_DEPENDENCY_REF', '').strip()
    if not library_ref and archive_info:
        library_ref = archive_info['dependency_commit']
    if library_ref.startswith('-') or any(c.isspace() for c in library_ref):
        raise SystemExit('Invalid dependency ref.')
    if not library_ref:
        # Newer Blender tags may pin ARM64 as a proper submodule.
        tree = git('ls-tree', 'HEAD', 'lib/linux_arm64', cwd=source, capture=True).strip()
        if tree.startswith('160000 commit '):
            library_ref = tree.split()[2]
        else:
            branch = f'blender-v{combined//100}.{combined%100}-release'
            refs = git('ls-remote', '--heads', LIBRARY_URL, f'refs/heads/{branch}', capture=True).strip()
            library_ref = refs.split()[0] if refs else 'refs/heads/main'
    libraries = source/'lib/linux_arm64'
    dependency_commit = checkout(libraries, LIBRARY_URL, library_ref)
    if library_ref == 'refs/heads/main' and not os.environ.get('BLENDER_DEPENDENCY_REF', '').strip():
        subject = git('log', '-1', '--format=%s', cwd=libraries, capture=True)
        declared = re.search(r'Blender (\d+\.\d+)', subject)
        series = f'{combined//100}.{combined%100}'
        if not declared or declared[1] != series:
            raise SystemExit('No matching release branch or identifiable main library bundle. '
                             'Set BLENDER_DEPENDENCY_REF to a compatible ARM64 library commit.')
    git('lfs', 'pull', '--include=*', '--exclude=', cwd=libraries)
    info = dict(version=requested, source_commit=source_commit, source_url=SOURCE_URL,
                dependency_commit=dependency_commit, dependency_ref=library_ref, dependency_url=LIBRARY_URL)
    (ROOT/'logs').mkdir(exist_ok=True)
    (ROOT/'logs/build-info.json').write_text(json.dumps(info, indent=2)+'\n')
    print(json.dumps(info, indent=2), flush=True)

if __name__ == '__main__':
    main()
