"""Check a factory-default desktop window, then close this test instance."""
import bpy
import gpu

def verify_ui():
    windows = list(bpy.context.window_manager.windows)
    has_viewport = any(area.type == "VIEW_3D" for window in windows for area in window.screen.areas)
    renderer = gpu.platform.renderer_get()
    if has_viewport and "llvmpipe" in renderer.lower():
        print("UI_VERIFIED", bpy.app.version_string, renderer, flush=True)
    else:
        print("UI_VERIFICATION_FAILED", len(windows), has_viewport, renderer, flush=True)
    bpy.ops.wm.quit_blender()
    return None

bpy.app.timers.register(verify_ui, first_interval=5)
