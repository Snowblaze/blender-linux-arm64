# Blender Linux ARM64

Unofficial stable Blender builds for Linux ARM64, with CPU Cycles rendering and automatic graphics selection. Download an installer from [Releases](https://github.com/Snowblaze/blender-linux-arm64/releases), or [build Blender yourself](#build-from-source) using the scripts in this repository.

Hosted packages target **Ubuntu 24.04 ARM64**. A local build has also been tested on **Raspberry Pi 5 with Debian 13**. Choose a package matching your distribution and release; these builds do not support every ARM64 CPU.

This project is not affiliated with or endorsed by the Blender Foundation.

## Install and run

Download the `.deb` installer and `SHA256SUMS` from the same release into one directory. Run these commands there, with only the installer you want to install in that directory:

```sh
sha256sum --ignore-missing -c SHA256SUMS
sudo apt install ./blender-linux-arm64_*.deb
blender
```

You can also open **Blender (ARM64 Community Build)** from your application menu. The package installs Blender under `/usr/lib/blender-linux-arm64` and adds the command at `/usr/bin/blender`.

The command supports Blender's normal command-line rendering and Python scripting arguments:

```sh
blender --version
blender --background --help
blender --background scene.blend --render-frame 1
```

To upgrade, install the newer `.deb` with the same `apt install` command. To uninstall:

```sh
sudo apt remove blender-linux-arm64
```

The package conflicts with the distribution's `blender` package because both provide `/usr/bin/blender`. APT will propose replacing that package when necessary.

If `blender` launches an older installation, check `command -v blender`. An existing `~/.local/bin/blender` may take priority over `/usr/bin/blender`; rename or remove that older launcher to use the package's command.

## Graphics selection

The command and desktop entry use **Auto** by default. Auto tests hardware **Vulkan first**, then **OpenGL**, and falls back to Mesa software OpenGL when neither works. This affects the viewport and EEVEE; Cycles rendering uses the CPU.

The first graphical launch runs a small factory-settings Workbench render for each hardware backend it tries. Each probe has a 20-second timeout. The choice is cached, so later launches reuse it. Changes to Blender, graphics drivers/devices, the kernel or relevant session settings invalidate the cache.

Override Auto for one launch:

```sh
BLENDER_GRAPHICS_MODE=hardware blender
BLENDER_GRAPHICS_MODE=software blender
```

Export `BLENDER_GRAPHICS_MODE` in your shell configuration for a persistent terminal preference. Probe logs and the cached choice are in `${XDG_CACHE_HOME:-~/.cache}/blender-linux-arm64/`; delete `graphics.json` to force another check.

Explicit `--gpu-backend` arguments bypass Auto's check. Help and version commands skip probing. Background CPU jobs use software OpenGL without probing, and Auto respects an inherited `LIBGL_ALWAYS_SOFTWARE=1`. The raw executable is available at `/usr/lib/blender-linux-arm64/blender`.

Auto checks backend startup and a small render. It does not guarantee that every scene or driver workload will work, and it does not relaunch Blender after an unrelated application crash.

## Compatibility and features

Packages are labelled with their build OS. APT resolves the required system libraries and versions during installation. Python and many dependencies are bundled, but the application still relies on system graphics, windowing and audio libraries.

Compiler flags include `-march=armv8.2-a+dotprod+fp16+lse`. Older ARM CPUs may lack these instructions. Local builds also default to native CPU optimization for Cycles; hosted builds disable that additional tuning. Compatibility with other distributions and devices requires separate testing.

The local Raspberry Pi 5 build was tested on Debian 13 (trixie), four Cortex-A76 cores, 16 GB RAM and Mesa 26.2.2. That driver exposes insufficient hardware OpenGL support and lacks Vulkan features Blender requires. Software OpenGL works on this setup, with limited viewport and EEVEE performance.

The feature configuration follows Blender's official Windows release preset with ARM64 exclusions, adapted for Linux windowing and audio.

- **Enabled:** CPU Cycles, OSL, Embree, path guiding, OpenImageDenoise, FFmpeg, Freestyle, USD/Hydra, MaterialX, Alembic, OpenVDB/NanoVDB, fluids, OpenXR, OpenGL and Vulkan.
- **Disabled:** CUDA, OptiX, HIP/HIPRT, oneAPI and their GPU kernels, standalone Cycles, the standalone Hydra render delegate, an importable `bpy` target, FriBidi and HarfBuzz.

The CPU-only package omits optional OpenImageDenoise GPU plugins, so it does not require NVIDIA, HIP or SYCL drivers. An enabled graphics backend still needs a compatible driver to use hardware acceleration.

## Build from source

Build on native Linux ARM64. The scripts fetch stable Blender source and official precompiled ARM64 libraries, then configure and compile Blender. They do not rebuild all dependencies; upstream dependency build recipes are included in Blender's source.

Install the initial tools and clone the repository:

```sh
sudo apt update
sudo apt install git git-lfs cmake ninja-build build-essential python3 xz-utils dpkg-dev binutils
git clone https://github.com/Snowblaze/blender-linux-arm64.git
cd blender-linux-arm64
```

Blender 5.2 requires GCC 14 or newer. On Ubuntu 24.04, install and select it before configuring:

```sh
sudo apt install gcc-14 g++-14
export CC=gcc-14 CXX=g++-14
```

Blender declares CMake 3.21 as its minimum. This recipe has been tested with CMake 3.31.6, GCC 14.2, Ninja and four build jobs. Allow several gigabytes for source, libraries, object files and installation. Compiler or dependency requirements can change in newer Blender releases.

Fetch the newest stable version, install the remaining build dependencies, and build:

```sh
./prepare-source.sh
sudo python3 source/build_files/build_environment/install_linux_packages.py
./build-blender.sh
```

To select a specific stable version, set `BLENDER_VERSION` when preparing the source, for example `BLENDER_VERSION=5.2.2 ./prepare-source.sh`. Alpha, beta and release-candidate tags are excluded from automatic selection.

The default installation is `~/.local/opt/blender-<version>-linux-arm64`, outside the checkout. Set `BLENDER_INSTALL_DIR` to an absolute path to choose another location, and use that setting for building, verification and packaging. Local builds produce the raw Blender executable; the Auto launcher is added by Debian packaging.

Running `./build-blender.sh` again resumes the build. Use `BLENDER_BUILD_JOBS=2 ./build-blender.sh` to reduce compile concurrency, or set `BLENDER_NATIVE_ONLY=OFF` to disable native Cycles tuning as the hosted workflow does. When changing compilers, choose a new `BLENDER_BUILD_DIR` because CMake caches the compiler selection. Feature overrides are in `config/windows-arm64-features.cmake`.

### Verify and launch your build

From the checkout, resolve the installation path and run the render and feature checks:

```bash
project_dir="$PWD"
source ./build-settings.sh
LIBGL_ALWAYS_SOFTWARE=1 "$install_dir/blender" --gpu-backend opengl -noaudio --background --factory-startup --python-exit-code 1 --python verify-build.py
```

From a graphical desktop session, check GUI startup:

```sh
LIBGL_ALWAYS_SOFTWARE=1 "$install_dir/blender" --gpu-backend opengl -noaudio --factory-startup --python-exit-code 1 --python verify-ui.py
```

The render test prints `BUILD_VERIFIED` on success. The GUI test prints `UI_VERIFIED` or `UI_VERIFICATION_FAILED` and closes its own Blender instance. Test images, the test scene and build logs are saved in `logs/`. The tests use factory settings and leave your normal startup file unchanged.

To launch the raw build with software graphics:

```sh
LIBGL_ALWAYS_SOFTWARE=1 "$install_dir/blender" --gpu-backend opengl
```

For creating installers and publishing builds, see [Releasing](RELEASING.md).

## Source and licensing

Blender source is unmodified. The binary distribution and repository scripts use **GPL-3.0-or-later**; see [LICENSE](LICENSE). Third-party copyright and license notices are preserved in the installation's `license/` directory. No warranty is provided.

Each packaged build includes `BUILD-INFO.json` with the selected version and exact source and ARM64 library commits, plus build OS, compiler, CPU optimization settings and recipe commit where available. The attached `blender-<version>-source.tar.xz` contains Blender source, required release/assets/scripts files, the build recipe and a dependency source manifest. Git metadata, precompiled libraries and unused test data are excluded.

Upstream source repositories: [Blender](https://projects.blender.org/blender/blender) and [Linux ARM64 libraries](https://projects.blender.org/blender/lib-linux_arm64).

`prepare-source.sh` selects a pinned ARM64 submodule, a matching release branch, or a main library bundle that identifies the selected Blender major/minor series. Set `BLENDER_DEPENDENCY_REF` to choose a compatible official library ref explicitly. The resolved commits are recorded in `logs/build-info.json`. Dependency version differences are reported; configuration and verification check whether the available bundle works with the source.

The manifest is generated from the selected Blender dependency recipes into `logs/dependency-sources.tsv` and included with packaged builds as `dependency-sources.tsv`. It lists filenames, versions, hashes and Blender mirror/upstream URLs, including dependencies for other platforms and build tools.

Download dependency source with checksum verification:

```sh
python3 fetch-dependency-source.py FFMPEG --output dependency-sources
python3 fetch-dependency-source.py --all --output dependency-sources
```

The downloader uses the packaged manifest or the generated manifest in `logs/`. Dependency build recipes and patches are under `source/build_files/build_environment/`; Blender's `make deps` target builds those libraries from source. If a source mirror becomes unavailable, open an issue so its location can be restored.

To reproduce a packaged build, extract the attached source archive and run `prepare-source.sh`. It uses the included version and exact library commit from `BUILD-INFO.json`. Follow the build and verification instructions above, selecting the recorded CPU optimization setting. Exact commits make inputs traceable; byte-for-byte reproducibility across different compilers and machines is not guaranteed.
