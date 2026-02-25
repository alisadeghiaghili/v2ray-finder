"""Entry point for PyInstaller EXE build of the plain CLI.

Usage (development)::

    python cli_entry.py [args]

Usage (build)::

    pyinstaller --onefile --name v2ray-finder --console cli_entry.py
"""
from v2ray_finder.cli import main

if __name__ == "__main__":
    main()
