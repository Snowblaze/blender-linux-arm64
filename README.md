# Blender Linux ARM64

Unofficial stable Blender builds for Linux ARM64, with a reusable build process, CPU rendering, and software OpenGL instructions. The original local build was tested on Raspberry Pi 5 with Debian 13. Hosted workflow builds use Ubuntu 24.04 ARM64.

This project is not affiliated with or endorsed by the Blender Foundation.

## Install and run

Download the ARM64 `.deb` installer and `SHA256SUMS` from a completed workflow's **Artifacts**, or from [Releases](https://github.com/Snowblaze/blender-linux-arm64/releases) once a build has been published there. Choose the package built for your distribution and release: for example, the local package targets Debian 13, while hosted workflow packages target Ubuntu 24.04. Replace the filename below with the downloaded installer.

```sh
sha256sum --ignore-missing -c SHA256SUMS
sudo apt install ./blender-linux-arm64_<version>-<revision>+<build-os>_arm64.deb
blender
# Command-line rendering and Python scripting are available too:
blender --background --help
```

The installer adds the application under `/usr/lib/blender-linux-arm64`, the command at `/usr/bin/blender`, and a desktop entry named **Blender (ARM64 Community Build)**. The command and desktop entry default to **Auto** graphics selection, passing all command-line arguments to Blender. Auto tests hardware Vulkan, then OpenGL, and falls back to Mesa software OpenGL if neither works. The raw executable remains available at `/usr/lib/blender-linux-arm64/blender` for compatible hardware graphics drivers.

An older `~/.local/bin/blender` takes priority if that directory appears first on PATH. Check `command -v blender`; if it points to your old local installation, remove or rename that old launcher to use the package's command.

This package conflicts with the distribution's `blender` package because both provide `/usr/bin/blender`. APT will propose replacing it when necessary. Uninstall the community package with `sudo apt remove blender-linux-arm64`. Install a newer `.deb` with the same `apt install` command to upgrade.

## Graphics selection

Auto runs a small, isolated factory-settings Workbench render to check the actual Blender backend, without opening your files or changing your preferences. Each hardware backend has a 20-second probe timeout. The result is cached per user/session and invalidated when the application, graphics drivers/devices, kernel or relevant graphics environment changes. Later launches reuse the result. Probe logs and the choice are in `${XDG_CACHE_HOME:-~/.cache}/blender-linux-arm64/`; deleting `graphics.json` forces a new check.

Override the default for one launch:

```sh
BLENDER_GRAPHICS_MODE=hardware blender
BLENDER_GRAPHICS_MODE=software blender
```

Export the variable in your shell configuration for a persistent terminal preference. Explicit `--gpu-backend` arguments bypass Auto's check. Help/version commands skip probing; background CPU jobs use software OpenGL without probing. An inherited `LIBGL_ALWAYS_SOFTWARE=1` is also respected in Auto mode. Graphics selection affects the viewport/EEVEE, not the CPU-only Cycles compute configuration. This preflight check does not guarantee that every scene or driver workload is supported; the actual application is not relaunched after an unrelated crash.

## Compatibility

Tested on Raspberry Pi 5: Debian 13 (trixie), Linux aarch64, four Cortex-A76 cores, 16 GB RAM, Mesa 26.2.2.

This is not a universal ARM64 binary. Compiler flags include `-march=armv8.2-a+dotprod+fp16+lse`. Local builds default to native CPU optimization for Cycles; the hosted workflow disables that extra tuning. Neither should be assumed compatible with all ARM64 CPUs. Older ARM CPUs and older Linux distributions may be incompatible. The package bundles Python and many libraries but is not a fully static application. Required system-library versions are generated with `dpkg-shlibdeps`; dynamically loaded graphics/windowing/audio dependencies are also declared, and APT resolves them on installation.

Pi 5 hardware OpenGL exposed by the tested driver is insufficient for Blender. Its Vulkan driver also lacks required features. Software OpenGL works, but viewport and EEVEE performance are limited.

## Features

The configuration uses the selected Blender version's official Windows release preset plus explicit ARM64 feature exclusions, adapted for native Linux windowing and audio. New major/minor releases may need updates to the feature overrides or verification scripts.

Enabled: CPU Cycles, OSL, Embree, path guiding, OpenImageDenoise, FFmpeg, Freestyle, USD/Hydra, MaterialX, Alembic, OpenVDB/NanoVDB, fluids, OpenXR, OpenGL and Vulkan backends.

Disabled: CUDA, OptiX, HIP/HIPRT, oneAPI and their GPU kernels, standalone Cycles, standalone Hydra render delegate, importable `bpy` target, FriBidi and HarfBuzz. The CPU-only `.deb` also omits optional OpenImageDenoise GPU plugins so it does not require NVIDIA, HIP or SYCL drivers. Enabling a graphics backend at build time does not guarantee a compatible driver on the running machine.

Use the included verification scripts to check rendering, enabled features, and GUI startup after building. Build logs are kept locally in `logs/`; the render verification script also writes its test images and scene there. Verification messages appear in the terminal.

## Rebuild

The reusable process has four stages: fetch pinned sources and official ARM libraries, install build packages, configure and build, then verify and package. It uses the official precompiled dependencies; it does not rebuild every dependency from scratch. Source-build recipes for those libraries are included in Blender's source.

Start from a clean checkout on native Linux ARM64:

```sh
sudo apt update
sudo apt install git git-lfs cmake ninja-build build-essential python3 xz-utils dpkg-dev binutils
git clone https://github.com/Snowblaze/blender-linux-arm64.git
cd blender-linux-arm64
```

Blender declares CMake 3.21 as its minimum; CMake 3.31.6 was tested for this recipe. The original build used CMake 3.31.6, GCC 14.2, Ninja, and four build jobs. Allow several gigabytes for sources, Git LFS libraries, object files, and packaging copies. The installation defaults to `~/.local/opt/blender-<version>-linux-arm64`, outside the checkout. Set `BLENDER_INSTALL_DIR` to an absolute path to change it; use the same setting when building, running the verification commands, and packaging.

The default native CPU settings target the machine performing the build; this is not a cross-compilation recipe.

Then fetch, install remaining build packages, compile and verify:

```bash
# Select a stable version (omit BLENDER_VERSION to resolve the newest stable tag):
export BLENDER_VERSION=5.2.2
./prepare-source.sh
sudo python3 source/build_files/build_environment/install_linux_packages.py
./build-blender.sh
project_dir="$PWD"
source ./build-settings.sh
LIBGL_ALWAYS_SOFTWARE=1 "$install_dir/blender" --gpu-backend opengl -noaudio --background --factory-startup --python-exit-code 1 --python verify-build.py
```

To check desktop startup and the software OpenGL viewport, run from a graphical desktop session:

```sh
LIBGL_ALWAYS_SOFTWARE=1 "$install_dir/blender" --gpu-backend opengl -noaudio --factory-startup --python verify-ui.py
```

The GUI test prints `UI_VERIFIED` or `UI_VERIFICATION_FAILED` and closes its own Blender instance. The render test prints `BUILD_VERIFIED` on success. Neither test changes your normal startup file.

`prepare-source.sh` checks out the exact source and official prebuilt ARM dependency commits for the selected release. It downloads required Git LFS assets. Dependency builds from source are described below.

## Source access, reproducibility and licensing

Each packaged build includes `BUILD-INFO.json` recording the selected stable Blender version and exact official Blender source and Linux ARM64 library commits. Workflow artifacts also include the build OS, compiler, CPU optimization setting and recipe commit.

The source archive `blender-<version>-source.tar.xz` contains the Blender source checkout, hydrated release/assets/scripts files, build scripts, feature configuration, workflow, source metadata and dependency source manifest. Git metadata, precompiled libraries and unused test-data assets are excluded.

The upstream repositories are:

- Blender: https://projects.blender.org/blender/blender
- ARM64 libraries: https://projects.blender.org/blender/lib-linux_arm64

`prepare-source.sh` resolves a stable release tag and matching library branch, a pinned ARM64 submodule when available, or an explicitly selected library ref. It records the resolved commits in `logs/build-info.json`. When no ARM64 release branch exists, it accepts `main` automatically only when the library commit explicitly identifies the selected Blender major/minor series. Dependency version differences are reported; configuration and verification determine whether the available library bundle works with the source.

`logs/dependency-sources.tsv` is regenerated from the selected Blender source's dependency recipes. It lists archive filenames, versions, hashes and official Blender mirror/upstream URLs. Packaging includes this generated manifest as `dependency-sources.tsv` alongside both binary and source. The manifest includes other-platform and build-tool dependencies too.

To download dependency source with checksum verification:

```sh
python3 fetch-dependency-source.py FFMPEG --output dependency-sources
python3 fetch-dependency-source.py --all --output dependency-sources
```

The downloader uses the packaged manifest, or the generated `logs/dependency-sources.tsv` in a recipe checkout. These sources are made available by the Blender project at the explicit URLs in the manifest. If a source mirror becomes unavailable, open an issue so its location can be restored.

Dependency source recipes and patches are in `source/build_files/build_environment/`; Blender's `make deps` target builds libraries from source. Using official precompiled ARM64 libraries is the normal application-build path in this repository.

To reproduce a packaged build, extract its source archive and run `prepare-source.sh`. It uses the included version and exact library commit from `BUILD-INFO.json`. Install the build prerequisites, then run `build-blender.sh`, using the recorded CPU optimization setting if different from the local default. Use the verification and packaging steps in this README. Exact commits make the inputs traceable; this does not promise byte-for-byte reproducibility across compilers and machines.

The binary distribution and repository scripts use GPL-3.0-or-later. The GPL text is in `LICENSE`; preserve the binary's `license/` directory and all third-party notices. The source, patches and build instructions are provided without additional restrictions.

The Blender source code is unmodified; this repository supplies build settings and packaging scripts. No warranty is provided.

## Package your build

After a successful build and verification:

```sh
./package-release.sh
```

This writes an ARM64 `.deb` installer, Blender source plus build recipe archive, `BUILD-INFO.json`, and `SHA256SUMS` to `release/`. It preserves third-party notices and adds command-line and desktop launchers with automatic hardware selection and software OpenGL fallback. Debian packages include generated shared-library dependencies and root-owned files; building them does not require root. Set `BLENDER_PACKAGE_REVISION` to a positive integer for another package revision of the same Blender version (default: `1`; the workflow uses its run number). Upload those assets to a GitHub release; commit the scripts and documentation to the repository. Downloaded source, libraries, build files, and release archives are excluded from Git commits.

Running `./build-blender.sh` again resumes the existing build. Lower compile concurrency with `BLENDER_BUILD_JOBS=2 ./build-blender.sh` if needed. Feature changes belong in `config/windows-arm64-features.cmake`. A build on different hardware or with changed features needs its own compatibility notes and verification; native builds are not guaranteed byte-for-byte identical.

## Manual GitHub Actions builds

Push this recipe and `.github/workflows/manual-build.yml` to the repository's default branch. In GitHub, open **Actions → Build Blender ARM64 → Run workflow**.

- **Blender version:** enter a stable version such as `5.2.2`, or leave blank to select the newest stable upstream tag at run time. Alpha, beta and release-candidate tags are excluded.
- **Dependency ref:** normally leave blank. If no matching ARM64 library branch or identifiable main bundle is available, supply a compatible official library commit/branch. The resolved commit is always recorded.

The workflow runs only when manually triggered; pushes, tags and new upstream releases do not start it. It builds natively on `ubuntu-24.04-arm`, verifies CPU rendering and software OpenGL under Xvfb, then uploads the `.deb` installer, source archive, checksums and build metadata as downloadable artifacts retained for 30 days. Diagnostic logs are retained for 14 days, including on failures. It does not publish a GitHub Release.

Hosted artifacts are labelled with their Ubuntu build OS; they are not the existing Debian/Pi 5 build. They need separate testing on the target device before publication. New upstream compiler requirements, dependency changes or feature changes can require updating this recipe.
