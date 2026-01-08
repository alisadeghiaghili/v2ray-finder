# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-08

### Added
- Initial release of v2ray-finder
- Python API for fetching V2Ray servers
- Lightweight CLI with interactive TUI
- Rich CLI with colored output and progress bars
- GUI application using PySide6 (Qt6)
- Support for vmess, vless, trojan, shadowsocks, ssr protocols
- GitHub repository search functionality
- Curated known sources aggregation
- Server deduplication and filtering
- Export to text files
- Protocol-based statistics
- Comprehensive test suite
- Full documentation in English and Persian

### Features
- **Core Library**: V2RayServerFinder class with flexible API
- **CLI Tools**: 
  - `v2ray-finder`: Lightweight interactive CLI
  - `v2ray-finder-rich`: Enhanced CLI with rich output
  - `v2ray-finder-gui`: Desktop GUI application
- **GitHub Integration**: Search and fetch from repositories
- **Known Sources**: Pre-configured high-quality sources
- **Cross-platform**: Windows, Linux, macOS support

### Technical Details
- Python ≥ 3.8 support
- PySide6 for GUI (Qt official binding)
- Rich library for enhanced CLI
- Requests for HTTP operations
- Pytest for testing
- Black/Flake8/isort for code quality

---

## [Unreleased]

### Planned
- Server health check functionality
- Filtering by country/region
- Export to multiple formats (JSON, YAML, Base64)
- Config validation
- Speed testing
- Automatic updates
- CI/CD integration

---

[0.1.0]: https://github.com/alisadeghiaghili/v2ray-finder/releases/tag/v0.1.0
