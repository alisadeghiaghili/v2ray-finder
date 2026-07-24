"""Lightweight Clash YAML proxy parser.

Parses Clash-format proxy configurations and converts them to standard
V2Ray/Xray URI strings.  Designed to work without PyYAML by using
indentation-aware line parsing.

Supported proxy types:
    vmess, vless, trojan, ss (Shadowsocks)

Example::

    from v2ray_finder.clash_parser import extract_clash_proxy_uris

    text = open("clash_config.yaml").read()
    uris = extract_clash_proxy_uris(text)
    for uri in uris:
        print(uri)
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Dict, List
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SIMPLE_PAIR_RE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*-\s*(.*)$")


def _strip_quotes(value: str) -> str:
    """Remove surrounding quotes from a YAML scalar value."""
    value = (value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_scalar(value: str) -> Any:
    """Parse a YAML scalar into a Python native type."""
    value = _strip_quotes(value.strip())
    low = value.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in {"null", "none", "~"}:
        return ""
    if value.isdigit():
        try:
            return int(value)
        except Exception:
            pass
    return value


def _split_inline_fields(text: str) -> List[str]:
    """Split comma-separated inline fields respecting quotes and brackets."""
    fields: List[str] = []
    buf: List[str] = []
    quote_char = ""
    depth = 0
    for ch in text:
        if quote_char:
            buf.append(ch)
            if ch == quote_char:
                quote_char = ""
            continue
        if ch in {'"', "'"}:
            quote_char = ch
            buf.append(ch)
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            fields.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        fields.append("".join(buf).strip())
    return fields


def _parse_inline_object(text: str) -> Dict[str, Any]:
    """Parse an inline YAML object ``{key: value, ...}``."""
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    out: Dict[str, Any] = {}
    for field in _split_inline_fields(text):
        if ":" not in field:
            continue
        key, value = field.split(":", 1)
        out[key.strip()] = _parse_scalar(value)
    return out


def _parse_proxy_items(text: str) -> List[Dict[str, Any]]:
    """Extract proxy entries from Clash YAML ``proxies:`` section.

    Uses indentation-aware parsing instead of full YAML parsing.
    Returns a list of dicts, each representing one proxy entry.
    """
    lines = text.splitlines()
    in_proxies = False
    proxies_indent = 0
    current: Dict[str, Any] | None = None
    items: List[Dict[str, Any]] = []

    def flush() -> None:
        nonlocal current
        if current:
            items.append(current)
        current = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if not in_proxies:
            if stripped == "proxies:" or stripped.startswith("proxies:"):
                in_proxies = True
                proxies_indent = indent
            continue
        if indent <= proxies_indent and not stripped.startswith("-"):
            flush()
            break
        m = _LIST_ITEM_RE.match(line)
        if m:
            flush()
            rest = m.group(1).strip()
            current = {}
            if rest.startswith("{"):
                current.update(_parse_inline_object(rest))
            elif rest:
                pair = _SIMPLE_PAIR_RE.match(rest)
                if pair:
                    current[pair.group(1)] = _parse_scalar(pair.group(2))
            continue
        if current is not None:
            pair = _SIMPLE_PAIR_RE.match(line)
            if pair:
                key, value = pair.group(1), pair.group(2)
                current[key] = _parse_scalar(value)
    flush()
    return items


# ---------------------------------------------------------------------------
# URI builders — convert Clash proxy dicts to standard V2Ray/Xray URIs
# ---------------------------------------------------------------------------


def _b64_json(data: Dict[str, Any]) -> str:
    """Base64-encode a dict as JSON (URL-safe, no padding)."""
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _vmess_uri(p: Dict[str, Any]) -> str:
    """Build a vmess:// URI from a Clash proxy dict."""
    net = str(p.get("network") or p.get("net") or "tcp")
    tls = bool(p.get("tls")) or str(p.get("tls") or "").lower() == "true"
    obj = {
        "v": "2",
        "ps": str(p.get("name") or "clash-vmess"),
        "add": str(p.get("server") or ""),
        "port": str(p.get("port") or "443"),
        "id": str(p.get("uuid") or ""),
        "aid": str(p.get("alterId") or p.get("alter-id") or "0"),
        "scy": str(p.get("cipher") or "auto"),
        "net": net,
        "type": "none",
        "host": str(p.get("servername") or p.get("sni") or p.get("host") or ""),
        "path": str(p.get("path") or "/"),
        "tls": "tls" if tls else "",
        "sni": str(p.get("servername") or p.get("sni") or ""),
    }
    return "vmess://" + _b64_json(obj)


def _trojan_uri(p: Dict[str, Any]) -> str:
    """Build a trojan:// URI from a Clash proxy dict."""
    password = quote(str(p.get("password") or ""), safe="")
    server = str(p.get("server") or "")
    port = str(p.get("port") or "443")
    params: List[str] = []
    sni = str(p.get("sni") or p.get("servername") or "")
    if sni:
        params.append("sni=" + quote(sni, safe=""))
    name = quote(str(p.get("name") or "clash-trojan"), safe="")
    query = ("?" + "&".join(params)) if params else ""
    return f"trojan://{password}@{server}:{port}{query}#{name}"


def _ss_uri(p: Dict[str, Any]) -> str:
    """Build an ss:// URI from a Clash proxy dict."""
    cipher = str(p.get("cipher") or "")
    password = str(p.get("password") or "")
    server = str(p.get("server") or "")
    port = str(p.get("port") or "443")
    userinfo = (
        base64.urlsafe_b64encode(f"{cipher}:{password}".encode()).decode().rstrip("=")
    )
    name = quote(str(p.get("name") or "clash-ss"), safe="")
    return f"ss://{userinfo}@{server}:{port}#{name}"


def _vless_uri(p: Dict[str, Any]) -> str:
    """Build a vless:// URI from a Clash proxy dict."""
    uuid = str(p.get("uuid") or "")
    server = str(p.get("server") or "")
    port = str(p.get("port") or "443")
    params: List[str] = []
    tls = bool(p.get("tls")) or str(p.get("tls") or "").lower() == "true"
    params.append("security=" + ("tls" if tls else "none"))
    net = str(p.get("network") or "tcp")
    params.append("type=" + quote(net, safe=""))
    sni = str(p.get("sni") or p.get("servername") or "")
    if sni:
        params.append("sni=" + quote(sni, safe=""))
    path = str(p.get("path") or "")
    if path:
        params.append("path=" + quote(path, safe=""))
    name = quote(str(p.get("name") or "clash-vless"), safe="")
    return f"vless://{uuid}@{server}:{port}?{'&'.join(params)}#{name}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def proxy_to_uri(proxy: Dict[str, Any]) -> str:
    """Convert a Clash proxy dict to a standard V2Ray/Xray URI string.

    Args:
        proxy: Clash proxy dict with keys like ``type``, ``server``,
               ``port``, ``uuid``, ``password``, ``cipher``, etc.

    Returns:
        Standard URI string (e.g. ``vmess://...``), or empty string
        if the proxy type is unsupported or required fields are missing.

    Examples::

        >>> proxy_to_uri({"type": "vmess", "server": "example.com",
        ...               "port": 443, "uuid": "abc-123"})
        'vmess://...'
    """
    proto = str(proxy.get("type") or "").lower()
    if not proxy.get("server") or not proxy.get("port"):
        return ""
    if proto == "vmess" and proxy.get("uuid"):
        return _vmess_uri(proxy)
    if proto == "trojan" and proxy.get("password"):
        return _trojan_uri(proxy)
    if proto == "ss" and proxy.get("cipher") and proxy.get("password"):
        return _ss_uri(proxy)
    if proto == "vless" and proxy.get("uuid"):
        return _vless_uri(proxy)
    return ""


def extract_clash_proxy_uris(text: str) -> List[str]:
    """Extract supported Clash proxies and return standard URI strings.

    Parses the ``proxies:`` section of a Clash YAML config and converts
    each supported proxy entry to a standard V2Ray/Xray URI.

    Args:
        text: Raw Clash YAML config text.

    Returns:
        Deduplicated list of URI strings.  Order is preserved.

    Examples::

        >>> yaml_text = '''
        ... proxies:
        ...   - name: my-server
        ...     type: vmess
        ...     server: example.com
        ...     port: 443
        ...     uuid: abc-123
        ... '''
        >>> uris = extract_clash_proxy_uris(yaml_text)
        >>> len(uris)
        1
        >>> uris[0].startswith("vmess://")
        True
    """
    uris: List[str] = []
    for item in _parse_proxy_items(text or ""):
        uri = proxy_to_uri(item)
        if uri:
            uris.append(uri)
    return list(dict.fromkeys(uris))
