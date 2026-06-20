using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using V2RayFinder.Core.Models;

namespace V2RayFinder.Core;

/// <summary>
/// Parses raw text and extracts V2Ray config URIs.
/// Supports vmess://, vless://, trojan://, ss://, ssr://
/// </summary>
public static class ConfigParser
{
    private static readonly Regex ConfigRegex = new(
        @"(vmess|vless|trojan|ss|ssr)://[^\s""'<>]+",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    public static IEnumerable<V2RayConfig> ExtractFromText(string text)
    {
        foreach (Match m in ConfigRegex.Matches(text))
        {
            var raw = m.Value.Trim();
            if (TryParse(raw, out var config))
                yield return config!;
        }
    }

    public static bool TryParse(string raw, out V2RayConfig? config)
    {
        config = null;
        if (string.IsNullOrWhiteSpace(raw)) return false;

        try
        {
            var protocol = DetectProtocol(raw);
            if (protocol == V2RayProtocol.Unknown) return false;

            var (host, port) = ExtractHostPort(raw, protocol);
            var fingerprint = ComputeFingerprint(raw);

            config = new V2RayConfig(raw, protocol, host, port, fingerprint);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static V2RayProtocol DetectProtocol(string raw)
    {
        if (raw.StartsWith("vmess://", StringComparison.OrdinalIgnoreCase))  return V2RayProtocol.Vmess;
        if (raw.StartsWith("vless://", StringComparison.OrdinalIgnoreCase))  return V2RayProtocol.Vless;
        if (raw.StartsWith("trojan://", StringComparison.OrdinalIgnoreCase)) return V2RayProtocol.Trojan;
        if (raw.StartsWith("ss://", StringComparison.OrdinalIgnoreCase))     return V2RayProtocol.Shadowsocks;
        if (raw.StartsWith("ssr://", StringComparison.OrdinalIgnoreCase))    return V2RayProtocol.Shadowsocks;
        return V2RayProtocol.Unknown;
    }

    private static (string? host, int? port) ExtractHostPort(string raw, V2RayProtocol protocol)
    {
        try
        {
            if (protocol == V2RayProtocol.Vmess)
            {
                // vmess://base64json
                var b64 = raw["vmess://".Length..];
                // Pad if needed
                b64 = b64.TrimEnd('#', '?');
                b64 = b64.PadRight(b64.Length + (4 - b64.Length % 4) % 4, '=');
                var json = Encoding.UTF8.GetString(Convert.FromBase64String(b64));
                var hostMatch = Regex.Match(json, @"""add""\s*:\s*""([^""]+)""");
                var portMatch = Regex.Match(json, @"""port""\s*:\s*[""']?(\d+)[""']?");
                var host = hostMatch.Success ? hostMatch.Groups[1].Value : null;
                var port = portMatch.Success ? int.Parse(portMatch.Groups[1].Value) : (int?)null;
                return (host, port);
            }
            else
            {
                // For vless, trojan, ss — parse as URI
                var uri = new Uri(raw.Split('#')[0]);
                return (uri.Host, uri.Port > 0 ? uri.Port : null);
            }
        }
        catch
        {
            return (null, null);
        }
    }

    public static string ComputeFingerprint(string raw)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(raw));
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }
}
