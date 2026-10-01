"""Run with the newly built Blender in background mode."""
from pathlib import Path
import platform
import os
import bpy
import numpy
import _cycles

expected_version = os.environ.get("BLENDER_VERSION")
if expected_version:
    assert bpy.app.version == tuple(map(int, expected_version.split("."))), bpy.app.version_string
assert platform.machine() == "aarch64", platform.machine()
device_types = _cycles.get_device_types()
assert not any(device_types), device_types
print("BACKENDS_VERIFIED Windows ARM64 profile: CPU-only Cycles compute", flush=True)
for feature in ("with_osl", "with_embree", "with_path_guiding", "with_openimagedenoise"):
    assert getattr(_cycles, feature), feature
print("CYCLES_FEATURES_VERIFIED OSL Embree path_guiding OpenImageDenoise", flush=True)
for feature in ("cycles", "cycles_osl", "codec_ffmpeg", "freestyle", "openvdb", "alembic", "usd", "fluid", "xr_openxr"):
    assert getattr(bpy.app.build_options, feature), feature
print("RELEASE_FEATURES_VERIFIED Cycles OSL FFmpeg Freestyle OpenVDB Alembic USD fluids OpenXR", flush=True)
project_dir = Path(__file__).resolve().parent
(project_dir / "logs").mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=False)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 4
scene.cycles.use_denoising = True
scene.render.resolution_x = 64
scene.render.resolution_y = 64
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(project_dir / "logs" / "smoke-render.png")
bpy.ops.render.render(write_still=True)
assert Path(scene.render.filepath).is_file()
bpy.ops.wm.save_as_mainfile(filepath=str(project_dir / "logs" / "smoke-scene.blend"))
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.filepath = str(project_dir / "logs" / "smoke-workbench.png")
bpy.ops.render.render(write_still=True)
assert Path(scene.render.filepath).is_file()
import gpu
print("GRAPHICS_VERIFIED", gpu.platform.renderer_get(), gpu.platform.version_get())
print("BUILD_VERIFIED", bpy.app.version_string, platform.machine(), "NumPy", numpy.__version__)
