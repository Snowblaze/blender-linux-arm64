# Follow the selected Blender version's official Windows buildbot release feature preset,
# while building a native Linux application. Do not fake WIN32 or change the
# platform toolchain: Linux must keep its own windowing and audio integration.
include("${CMAKE_CURRENT_LIST_DIR}/../source/build_files/buildbot/config/blender_windows.cmake")

# The upstream Windows ARM64 target excludes these options in CMakeLists.txt
# and skips enabling them in blender_release.cmake. Explicit overrides are
# needed here because the host platform is Linux and an existing cache is used.
set(WITH_CYCLES_DEVICE_CUDA       OFF CACHE BOOL "" FORCE)
set(WITH_CYCLES_DEVICE_OPTIX      OFF CACHE BOOL "" FORCE)
set(WITH_CYCLES_DEVICE_HIP        OFF CACHE BOOL "" FORCE)
set(WITH_CYCLES_DEVICE_HIPRT      OFF CACHE BOOL "" FORCE)
set(WITH_CYCLES_DEVICE_ONEAPI     OFF CACHE BOOL "" FORCE)
set(WITH_CYCLES_CUDA_BINARIES     OFF CACHE BOOL "" FORCE)
set(WITH_CYCLES_HIP_BINARIES      OFF CACHE BOOL "" FORCE)
set(WITH_CYCLES_ONEAPI_BINARIES   OFF CACHE BOOL "" FORCE)
set(WITH_TBB_MALLOC_PROXY         OFF CACHE BOOL "" FORCE)

# These optional application targets and shaping libraries are not enabled
# by the official release preset. Reset any prior local cache values.
set(WITH_CYCLES_STANDALONE             OFF CACHE BOOL "" FORCE)
set(WITH_CYCLES_STANDALONE_GUI         OFF CACHE BOOL "" FORCE)
set(WITH_CYCLES_HYDRA_RENDER_DELEGATE   OFF CACHE BOOL "" FORCE)
set(WITH_PYTHON_MODULE                 OFF CACHE BOOL "" FORCE)
set(WITH_FRIBIDI                       OFF CACHE BOOL "" FORCE)
set(WITH_HARFBUZZ                      OFF CACHE BOOL "" FORCE)

# Both Windows ARM64 and Linux release targets support these graphics APIs.
set(WITH_OPENGL_BACKEND ON CACHE BOOL "" FORCE)
set(WITH_VULKAN_BACKEND ON CACHE BOOL "" FORCE)
