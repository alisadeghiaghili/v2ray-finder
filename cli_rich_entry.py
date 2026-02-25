"""Entry point for PyInstaller EXE build of the Rich CLI.

Usage (development)::

    python cli_rich_entry.py [args]

Usage (build)::

    pyinstaller --onefile --name v2ray-finder-rich --console cli_rich_entry.py
"""
from v2ray_finder.cli_rich import main

if __name__ == "__main__":
    main()
