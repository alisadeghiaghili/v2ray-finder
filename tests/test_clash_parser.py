"""Tests for the Clash YAML proxy parser."""

from __future__ import annotations

import pytest

from v2ray_finder.clash_parser import (
    _parse_proxy_items,
    _parse_scalar,
    _strip_quotes,
    extract_clash_proxy_uris,
    proxy_to_uri,
)

# ---------------------------------------------------------------------------
# _strip_quotes
# ---------------------------------------------------------------------------


class TestStripQuotes:
    def test_double_quoted(self) -> None:
        assert _strip_quotes('"hello"') == "hello"

    def test_single_quoted(self) -> None:
        assert _strip_quotes("'hello'") == "hello"

    def test_no_quotes(self) -> None:
        assert _strip_quotes("hello") == "hello"

    def test_empty(self) -> None:
        assert _strip_quotes("") == ""

    def test_whitespace(self) -> None:
        assert _strip_quotes('  "hello"  ') == "hello"


# ---------------------------------------------------------------------------
# _parse_scalar
# ---------------------------------------------------------------------------


class TestParseScalar:
    def test_bool_true(self) -> None:
        assert _parse_scalar("true") is True

    def test_bool_false(self) -> None:
        assert _parse_scalar("false") is False

    def test_int(self) -> None:
        assert _parse_scalar("443") == 443

    def test_string(self) -> None:
        assert _parse_scalar("hello") == "hello"

    def test_null(self) -> None:
        assert _parse_scalar("null") == ""

    def test_quoted_string(self) -> None:
        assert _parse_scalar('"hello world"') == "hello world"


# ---------------------------------------------------------------------------
# proxy_to_uri
# ---------------------------------------------------------------------------


class TestProxyToUri:
    def test_vmess(self) -> None:
        import base64
        import json

        proxy = {
            "type": "vmess",
            "server": "example.com",
            "port": 443,
            "uuid": "abc-123-def",
        }
        uri = proxy_to_uri(proxy)
        assert uri.startswith("vmess://")
        # vmess URI is base64-encoded, so decode and verify
        raw = uri[len("vmess://") :]
        raw += "=" * (-len(raw) % 4)
        data = json.loads(base64.urlsafe_b64decode(raw))
        assert data["add"] == "example.com"
        assert data["port"] == "443"
        assert data["id"] == "abc-123-def"

    def test_vless(self) -> None:
        proxy = {
            "type": "vless",
            "server": "example.com",
            "port": 443,
            "uuid": "abc-123-def",
        }
        uri = proxy_to_uri(proxy)
        assert uri.startswith("vless://")
        assert "example.com" in uri

    def test_trojan(self) -> None:
        proxy = {
            "type": "trojan",
            "server": "example.com",
            "port": 443,
            "password": "mypassword",
        }
        uri = proxy_to_uri(proxy)
        assert uri.startswith("trojan://")
        assert "example.com" in uri

    def test_ss(self) -> None:
        proxy = {
            "type": "ss",
            "server": "example.com",
            "port": 443,
            "cipher": "aes-256-gcm",
            "password": "mypassword",
        }
        uri = proxy_to_uri(proxy)
        assert uri.startswith("ss://")
        assert "example.com" in uri

    def test_unsupported_type(self) -> None:
        proxy = {"type": "socks5", "server": "example.com", "port": 1080}
        assert proxy_to_uri(proxy) == ""

    def test_missing_server(self) -> None:
        proxy = {"type": "vmess", "port": 443, "uuid": "abc"}
        assert proxy_to_uri(proxy) == ""

    def test_missing_port(self) -> None:
        proxy = {"type": "vmess", "server": "example.com", "uuid": "abc"}
        assert proxy_to_uri(proxy) == ""


# ---------------------------------------------------------------------------
# extract_clash_proxy_uris
# ---------------------------------------------------------------------------


class TestExtractClashProxyUris:
    def test_empty_input(self) -> None:
        assert extract_clash_proxy_uris("") == []
        assert extract_clash_proxy_uris(None) == []  # type: ignore[arg-type]

    def test_vmess_proxy(self) -> None:
        yaml = """
proxies:
  - name: my-server
    type: vmess
    server: example.com
    port: 443
    uuid: abc-123-def
    alterId: 0
    cipher: auto
"""
        uris = extract_clash_proxy_uris(yaml)
        assert len(uris) == 1
        assert uris[0].startswith("vmess://")

    def test_vless_proxy(self) -> None:
        yaml = """
proxies:
  - name: vless-server
    type: vless
    server: vless.example.com
    port: 443
    uuid: abc-123-def
    tls: true
"""
        uris = extract_clash_proxy_uris(yaml)
        assert len(uris) == 1
        assert uris[0].startswith("vless://")

    def test_trojan_proxy(self) -> None:
        yaml = """
proxies:
  - name: trojan-server
    type: trojan
    server: trojan.example.com
    port: 443
    password: mypassword
"""
        uris = extract_clash_proxy_uris(yaml)
        assert len(uris) == 1
        assert uris[0].startswith("trojan://")

    def test_ss_proxy(self) -> None:
        yaml = """
proxies:
  - name: ss-server
    type: ss
    server: ss.example.com
    port: 443
    cipher: aes-256-gcm
    password: mypassword
"""
        uris = extract_clash_proxy_uris(yaml)
        assert len(uris) == 1
        assert uris[0].startswith("ss://")

    def test_multiple_proxies(self) -> None:
        yaml = """
proxies:
  - name: server1
    type: vmess
    server: s1.example.com
    port: 443
    uuid: abc-123
  - name: server2
    type: vless
    server: s2.example.com
    port: 443
    uuid: def-456
  - name: server3
    type: trojan
    server: s3.example.com
    port: 443
    password: pass123
"""
        uris = extract_clash_proxy_uris(yaml)
        assert len(uris) == 3

    def test_deduplication(self) -> None:
        # Exact duplicates (same name, server, uuid) should be deduplicated
        yaml = """
proxies:
  - name: server1
    type: vless
    server: example.com
    port: 443
    uuid: abc-123
  - name: server1
    type: vless
    server: example.com
    port: 443
    uuid: abc-123
"""
        uris = extract_clash_proxy_uris(yaml)
        assert len(uris) == 1

    def test_no_dedup_different_names(self) -> None:
        # Different names produce different URIs (dedup happens at normalizer level)
        yaml = """
proxies:
  - name: server1
    type: vmess
    server: example.com
    port: 443
    uuid: abc-123
  - name: server1-dup
    type: vmess
    server: example.com
    port: 443
    uuid: abc-123
"""
        uris = extract_clash_proxy_uris(yaml)
        # Different names = different base64 payloads = different URIs
        assert len(uris) == 2

    def test_inline_yaml(self) -> None:
        yaml = "proxies:\n  - {name: test, type: vmess, server: ex.com, port: 443, uuid: abc}"
        uris = extract_clash_proxy_uris(yaml)
        assert len(uris) == 1
        assert uris[0].startswith("vmess://")

    def test_no_proxies_section(self) -> None:
        yaml = """
rules:
  - MATCH,DIRECT
"""
        assert extract_clash_proxy_uris(yaml) == []

    def test_comments_ignored(self) -> None:
        yaml = """
# This is a comment
proxies:
  # proxy entry
  - name: test
    type: vmess
    server: example.com
    port: 443
    uuid: abc-123
"""
        uris = extract_clash_proxy_uris(yaml)
        assert len(uris) == 1
