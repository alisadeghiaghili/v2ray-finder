[app]

title = V2Ray Finder
package.name = v2rayfinder
package.domain = org.mehdimt

source.dir = .
source.include_exts = py,kv,txt,md,toml,json
source.exclude_dirs = .git,.github,tests,docs,htmlcov,build,dist,.venv,venv,__pycache__,src
source.exclude_patterns = *.pyc,*.pyo,*.pyd,*.so,*.dylib,*.dll

version = 1.0.0
requirements = python3==3.11.9,hostpython3==3.11.9,kivy,openssl,requests

presplash.filename =
icon.filename =
orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 35
android.minapi = 23
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = False
android.release_artifact = apk

p4a.bootstrap = sdl2

log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1
