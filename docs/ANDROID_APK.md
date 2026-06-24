# Android APK build guide

This branch adds a mobile Android frontend for `v2ray-finder` using Kivy and Buildozer.

## What is included

- `main.py` — touch-first mobile UI for Android and desktop testing.
- `buildozer.spec` — Android packaging configuration.
- `.github/workflows/android-apk.yml` — GitHub Actions workflow that builds a debug APK and uploads it as an artifact.

## Mobile feature set

The first Android release supports:

- fetching public V2Ray/Xray config links through the existing `Pipeline`
- optional TCP health checking
- score and grade display
- fetched / unique / healthy / scored statistics
- stop button with `StopController`
- copy all results to clipboard
- save results to the app data directory

Layer-3 xray / Google-204 probing is intentionally disabled in the Android UI for now. Running the native xray binary inside an APK needs a separate Android-specific packaging strategy.

## Build APK on GitHub

1. Push this branch to GitHub.
2. Open the repository on GitHub.
3. Go to **Actions**.
4. Select **Build Android APK**.
5. Click **Run workflow**.
6. When the workflow finishes, download the artifact named `v2ray-finder-debug-apk`.

The workflow builds a debug APK from `buildozer.spec` and uploads `bin/*.apk`.

## Build locally on Linux or WSL

Install Buildozer:

```bash
python -m pip install --upgrade pip wheel setuptools
python -m pip install buildozer cython
```

Then run:

```bash
buildozer android debug
```

The APK will be created in the `bin/` directory.

## Test the UI on desktop

Install Kivy and run:

```bash
python -m pip install kivy requests
python main.py
```

## Important notes

- The APK needs the Android `INTERNET` permission.
- Keep the first mobile runs small, for example limit `100` or `200`, because Android devices are slower than desktop machines.
- Health checking can be slow because it opens TCP connections to many servers.
- If the APK build fails because of Android SDK/NDK download issues, rerun the workflow once; Buildozer downloads a large toolchain on the first run.
