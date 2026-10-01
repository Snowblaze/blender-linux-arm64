#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Select a working graphics backend before launching the packaged Blender."""
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile

GRAPHICS_POLICY = 'vulkan-first-v1'

PROBE = '''import bpy, gpu
bpy.ops.wm.read_factory_settings(use_empty=False)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 8
scene.render.resolution_y = 8
scene.render.resolution_percentage = 100
bpy.ops.render.render()
renderer = gpu.platform.renderer_get()
assert gpu.platform.device_type_get() != "SOFTWARE", renderer
assert not any(x in renderer.lower() for x in ("llvmpipe", "softpipe", "lavapipe")), renderer
assert gpu.platform.backend_type_get() == "EXPECTED_BACKEND"
print("BLENDER_HARDWARE_PROBE_OK", flush=True)
'''


def fingerprint(program, environment):
    """Invalidate the cache after application, driver, device or session changes."""
    paths = [program, program.parent/'BUILD-INFO.json', Path(__file__).resolve()]
    for directory in ['/dev/dri', '/usr/lib/aarch64-linux-gnu/dri', '/usr/share/vulkan/icd.d']:
        location = Path(directory)
        paths.append(location)
        if location.is_dir():
            paths.extend(sorted(location.iterdir()))
    for name in ['libEGL_mesa.so.0', 'libGLX_mesa.so.0', 'libvulkan.so.1']:
        paths.append(Path('/usr/lib/aarch64-linux-gnu')/name)
    records = []
    for path in paths:
        try:
            stat = path.stat()
            records.append((str(path), stat.st_size, stat.st_mtime_ns, stat.st_ino,
                            stat.st_mode, stat.st_uid, stat.st_gid))
        except OSError:
            records.append((str(path), None))
    variables = ['DISPLAY', 'WAYLAND_DISPLAY', 'XDG_SESSION_TYPE', 'LD_LIBRARY_PATH',
                 'DRI_PRIME', 'MESA_LOADER_DRIVER_OVERRIDE', 'MESA_VK_DEVICE_SELECT',
                 'VK_ICD_FILENAMES', 'VK_DRIVER_FILES', 'GALLIUM_DRIVER']
    data = [GRAPHICS_POLICY, platform.release(), os.getuid(), os.getgroups(), records,
            {key: environment.get(key) for key in variables}]
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def hardware_works(program, backend, environment, log_path):
    command = [str(program), '--gpu-backend', backend, '-noaudio', '--background',
               '--factory-startup', '--python-exit-code', '1', '--python-expr',
               PROBE.replace('EXPECTED_BACKEND', backend.upper())]
    process = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True)
    try:
        output, _ = process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        output, _ = process.communicate()
    try:
        log_path.write_bytes(output)
    except OSError:
        pass
    return process.returncode == 0 and b'BLENDER_HARDWARE_PROBE_OK' in output


def select_graphics(program, environment, cache_dir):
    key = fingerprint(program, environment)
    cache = cache_dir/'graphics.json'
    try:
        entry = json.loads(cache.read_text())
        if entry.get('fingerprint') == key and entry.get('backend') in ['opengl', 'vulkan']:
            if entry.get('mode') in ['hardware', 'software']:
                return entry['mode'], entry['backend']
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    try:
        cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError:
        pass
    mode, backend = 'software', 'opengl'
    for candidate in ['vulkan', 'opengl']:
        if hardware_works(program, candidate, environment, cache_dir/f'probe-{candidate}.log'):
            mode, backend = 'hardware', candidate
            break
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=cache_dir, delete=False) as file:
            json.dump(dict(fingerprint=key, mode=mode, backend=backend), file)
            temporary = Path(file.name)
        os.replace(temporary, cache)
    except OSError:
        # A read-only home/cache must not prevent launching Blender.
        if 'temporary' in locals():
            temporary.unlink(missing_ok=True)
    return mode, backend


def launch(program, arguments, environment, cache_dir):
    mode = environment.get('BLENDER_GRAPHICS_MODE', 'auto').lower()
    if mode not in ['auto', 'hardware', 'software']:
        raise SystemExit('BLENDER_GRAPHICS_MODE must be auto, hardware or software.')
    backend_args = []
    information_only = any(x in arguments for x in ['--help', '-h', '/?', '--version', '-v'])
    explicit_backend = any(x == '--gpu-backend' or x.startswith('--gpu-backend=') for x in arguments)
    if information_only or (mode == 'auto' and explicit_backend):
        return [str(program), *arguments], environment
    if mode == 'hardware':
        environment.pop('LIBGL_ALWAYS_SOFTWARE', None)
    elif mode == 'software':
        environment['LIBGL_ALWAYS_SOFTWARE'] = '1'
        if not explicit_backend:
            backend_args = ['--gpu-backend', 'opengl']
    elif environment.get('LIBGL_ALWAYS_SOFTWARE', '').lower() in ['1', 'true', 'yes']:
        backend_args = ['--gpu-backend', 'opengl']
    elif any(x in arguments for x in ['--background', '-b']):
        # CPU-only batch jobs need no hardware probe. Scripts that initialize a
        # viewport or Workbench can still use software OpenGL in the same process.
        environment['LIBGL_ALWAYS_SOFTWARE'] = '1'
        backend_args = ['--gpu-backend', 'opengl']
    else:
        probe_environment = dict(environment)
        probe_environment.pop('LIBGL_ALWAYS_SOFTWARE', None)
        selected, backend = select_graphics(program, probe_environment, cache_dir)
        if selected == 'software':
            environment['LIBGL_ALWAYS_SOFTWARE'] = '1'
        else:
            environment.pop('LIBGL_ALWAYS_SOFTWARE', None)
        backend_args = ['--gpu-backend', backend]
    return [str(program), *backend_args, *arguments], environment


def main():
    # The launcher is installed beside the executable; /usr/bin/blender symlinks here.
    program = Path(__file__).resolve().parent/'blender'
    cache_dir = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home()/'.cache')))/'blender-linux-arm64'
    command, environment = launch(program, sys.argv[1:], dict(os.environ), cache_dir)
    os.execve(program, command, environment)


if __name__ == '__main__':
    main()
