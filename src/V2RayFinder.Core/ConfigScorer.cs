using V2RayFinder.Core.Models;

namespace V2RayFinder.Core;

/// <summary>
/// Computes a quality score for each config.
/// Dimensions: latency, health, protocol preference, uniqueness, freshness.
/// Equivalent to Python's scorer module (A–F grades).
/// </summary>
public static class ConfigScorer
{
    // Protocol preference weights (vless/trojan tend to be more stable)
    private static readonly Dictionary<V2RayProtocol, double> ProtocolWeight = new()
    {
        [V2RayProtocol.Vless]       = 1.0,
        [V2RayProtocol.Trojan]      = 0.95,
        [V2RayProtocol.Vmess]       = 0.85,
        [V2RayProtocol.Shadowsocks] = 0.80,
        [V2RayProtocol.Unknown]     = 0.50,
    };

    public static IReadOnlyList<ConfigScore> Score(
        IEnumerable<V2RayConfig> configs,
        IReadOnlyDictionary<string, HealthResult>? healthResults = null)
    {
        var list = configs.ToList();
        if (list.Count == 0) return Array.Empty<ConfigScore>();

        // Build scores
        var raw = list.Select(c => ComputeScore(c, healthResults)).ToList();

        // Sort descending
        raw.Sort((a, b) => b.Total.CompareTo(a.Total));
        return raw;
    }

    private static ConfigScore ComputeScore(
        V2RayConfig config,
        IReadOnlyDictionary<string, HealthResult>? health)
    {
        double score = 0.0;

        // 1. Protocol weight (25%)
        score += 0.25 * ProtocolWeight.GetValueOrDefault(config.Protocol, 0.5);

        // 2. Has host & port (10%)
        if (config.Host != null && config.Port != null)
            score += 0.10;

        // 3. Health check (50%)
        if (health != null && health.TryGetValue(config.Fingerprint, out var h))
        {
            if (h.IsHealthy)
            {
                score += 0.50;

                // 4. Latency bonus (15%) — lower is better, cap at 5000ms
                var latencyScore = Math.Max(0, 1.0 - h.LatencyMs / 5000.0);
                score += 0.15 * latencyScore;
            }
        }
        else
        {
            // No health data — give partial credit
            score += 0.15;
        }

        score = Math.Clamp(score, 0.0, 1.0);
        var grade = ConfigScore.CalculateGrade(score);
        var latencyMs = health?.GetValueOrDefault(config.Fingerprint)?.LatencyMs ?? 0;

        return new ConfigScore(config.Raw, config.Protocol, score, grade, latencyMs);
    }
}
