# Releasing Blender Linux ARM64

This document covers generating installers and publishing builds. Installation, feature compatibility, building from source and verification are documented in [README.md](README.md).

## Publish through GitHub Actions

In the repository, open **Actions → Build Blender ARM64 → Run workflow** and select `main` with the desired build recipe.

- **Blender version:** leave blank to select the newest stable upstream tag, or enter a stable version such as `5.2.2`.
- **Dependency ref:** normally leave blank. Supply a compatible official ARM64 library commit or branch when automatic selection cannot find a matching bundle. The resolved commit is always recorded.

The workflow runs only when manually triggered. Pushes, tags and new upstream Blender releases do not start it.

The runner builds natively on Ubuntu 24.04 ARM64 with GCC 14 and native Cycles tuning disabled. It checks CPU rendering, enabled features, software OpenGL and GUI startup under Xvfb. It then creates the Debian package, installs it on the runner, and tests its command and Auto graphics launcher.

After verification passes, the workflow uploads build artifacts and publishes a GitHub Release with the same files. Publishing uses the built-in `GITHUB_TOKEN` with `contents: write` permission; no personal access token is needed. The release tag points to the exact recipe commit used by the workflow.

Tags include the Blender version, OS, run number and attempt, for example `v5.2.2-ubuntu24.04-arm64-r4-a1`. Rebuilds and reruns receive separate tags and releases.

## Release contents

Each published release has a version/build title, installation and compatibility notes, a link to its workflow logs, and four attached files:

| File | Contents |
| --- | --- |
| `blender-linux-arm64_<version>-<revision>+<build-os>_arm64.deb` | Installer with command-line and desktop launchers and automatic graphics selection. |
| `blender-<version>-source.tar.xz` | Blender source, build scripts, feature configuration, documentation, workflow and dependency source manifest. |
| `BUILD-INFO.json` | Resolved source and library commits, build environment, CPU settings and package metadata. |
| `SHA256SUMS` | Checksums for the installer, source archive and metadata. |

GitHub also provides its standard source ZIP and tarball for the tagged repository commit. Those contain this repository's build recipe; the attached source archive includes Blender's source.

Build artifacts are retained in Actions for 30 days. Diagnostic logs are uploaded on both success and failure and retained for 14 days. GitHub Release assets are separate from those temporary artifacts.

Hosted installers target Ubuntu 24.04 ARM64. Packages built locally use the local distribution label, such as `debian13`. Compatibility with other distributions and devices requires separate testing.

## Package a local build

Build and verify Blender using the instructions in [README.md](README.md), then run:

```sh
./package-release.sh
```

Keep the same `BLENDER_INSTALL_DIR` setting if you chose a custom installation. Packaging writes the installer, source archive, metadata and checksums to `release/`. It preserves third-party license notices, adds the Auto launcher and desktop integration, and generates system-library dependencies with `dpkg-shlibdeps`. Package files are root-owned; creating them does not require root.

The default package revision is `1`. Set a positive revision for another build of the same Blender version:

```sh
BLENDER_PACKAGE_REVISION=2 ./package-release.sh
```

The workflow uses its run number as the package revision. Check the generated assets from their output directory:

```sh
cd release
sha256sum -c SHA256SUMS
```

To publish a local package, create a release in the repository's **Releases** page, select the recipe commit used for that build, and attach the four files listed above. Describe the actual build OS and tested hardware in its notes. Local packaging prepares files; the GitHub Actions workflow performs automatic publication for hosted builds.

Source checkouts, downloaded libraries, build directories, logs and generated release files are ignored by Git. Commit the build recipe and documentation, and attach generated installers and archives to releases.
