using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using V2RayFinder.Core.Models;

namespace V2RayFinder.Core;

/// <summary>
/// Main orchestrator: fetch → parse → deduplicate → health check → score.
/// Equivalent to Python's Pipeline class with StopController support.
/// 
/// Usage:
///   var pipeline = new Pipeline(checkHealth: true);
///   var result = await pipeline.RunAsync(cancellationToken);
///   foreach (var s in result.Scores.Take(10))
///       Console.WriteLine($"{s.Grade}  {s.Total:F3}  {s.Config[..80]}");
/// </summary>
public sealed class Pipeline
{
    private readonly bool _checkHealth;
    private readonly int _fetchConcurrency;
    private readonly int _healthConcurrency;
    private readonly int _limit;
    private readonly TimeSpan _fetchTimeout;
    private readonly TimeSpan _healthTimeout;
    private readonly ILogger<Pipeline> _logger;
    private readonly IReadOnlyList<string> _sources;

    public Pipeline(
        bool checkHealth = false,
        int fetchConcurrency = 10,
        int healthConcurrency = 50,
        int limit = 0,
        TimeSpan? fetchTimeout = null,
        TimeSpan? healthTimeout = null,
        IReadOnlyList<string>? sources = null,
        ILogger<Pipeline>? logger = null)
    {
        _checkHealth       = checkHealth;
        _fetchConcurrency  = fetchConcurrency;
        _healthConcurrency = healthConcurrency;
        _limit             = limit;
        _fetchTimeout      = fetchTimeout  ?? TimeSpan.FromSeconds(15);
        _healthTimeout     = healthTimeout ?? TimeSpan.FromSeconds(5);
        _sources           = sources ?? SubscriptionSources.Urls;
        _logger            = logger ?? NullLogger<Pipeline>.Instance;
    }

    public delegate void ProgressCallback(string stage, int current, int total, string message);

    /// <summary>Runs the full pipeline. CancellationToken acts as StopController.</summary>
    public async Task<PipelineResult> RunAsync(
        CancellationToken ct = default,
        ProgressCallback? onProgress = null)
    {
        // ── Stage 1: Fetch ────────────────────────────────────────────────────
        Report(onProgress, "fetch", 0, _sources.Count, "Fetching subscription sources...");
        _logger.LogInformation("Fetching {count} sources with concurrency={c}", _sources.Count, _fetchConcurrency);

        using var fetcher = new SubscriptionFetcher(
            maxConcurrency: _fetchConcurrency,
            timeout: _fetchTimeout);

        var fetchResults = await fetcher.FetchAllAsync(_sources, ct);

        var allLines = fetchResults
            .Where(r => r.Success)
            .SelectMany(r => r.RawLines)
            .ToList();

        _logger.LogInformation("Fetched {lines} raw lines from {ok}/{total} sources",
            allLines.Count, fetchResults.Count(r => r.Success), fetchResults.Count);

        Report(onProgress, "fetch", _sources.Count, _sources.Count,
            $"Done — {fetchResults.Count(r => r.Success)} sources OK");

        ct.ThrowIfCancellationRequested();

        // ── Stage 2: Parse ────────────────────────────────────────────────────
        Report(onProgress, "parse", 0, allLines.Count, "Parsing configs...");
        _logger.LogInformation("Parsing {count} lines", allLines.Count);

        var parsed = allLines
            .AsParallel()
            .WithCancellation(ct)
            .SelectMany(line => ConfigParser.ExtractFromText(line))
            .ToList();

        _logger.LogInformation("Parsed {count} raw configs", parsed.Count);

        // ── Stage 3: Deduplicate ──────────────────────────────────────────────
        Report(onProgress, "dedup", 0, 1, "Deduplicating...");
        var unique = parsed
            .GroupBy(c => c.Fingerprint)
            .Select(g => g.First())
            .ToList();

        _logger.LogInformation("Deduplicated: {before} → {after}", parsed.Count, unique.Count);

        if (_limit > 0 && unique.Count > _limit)
            unique = unique.Take(_limit).ToList();

        ct.ThrowIfCancellationRequested();

        // ── Stage 4: Health check (optional) ─────────────────────────────────
        Dictionary<string, HealthResult>? healthMap = null;
        int healthyCount = 0;

        if (_checkHealth)
        {
            Report(onProgress, "health", 0, unique.Count, "Health-checking configs...");
            _logger.LogInformation("Health-checking {count} configs", unique.Count);

            var checker = new HealthChecker(concurrency: _healthConcurrency, tcpTimeout: _healthTimeout);
            var healthResults = await checker.CheckAllAsync(unique, ct);

            healthMap = healthResults.ToDictionary(h => ConfigParser.ComputeFingerprint(h.Config));
            healthyCount = healthResults.Count(h => h.IsHealthy);

            _logger.LogInformation("Health: {healthy}/{total} healthy", healthyCount, unique.Count);
            Report(onProgress, "health", unique.Count, unique.Count, $"{healthyCount} healthy");
        }

        ct.ThrowIfCancellationRequested();

        // ── Stage 5: Score ────────────────────────────────────────────────────
        Report(onProgress, "score", 0, 1, "Scoring configs...");

        // Filter to healthy-only if we have health data
        var toScore = _checkHealth && healthMap != null
            ? unique.Where(c => healthMap.TryGetValue(c.Fingerprint, out var h) && h.IsHealthy).ToList()
            : unique;

        var scores = ConfigScorer.Score(toScore, healthMap);
        _logger.LogInformation("Scored {count} configs", scores.Count);

        Report(onProgress, "score", 1, 1, $"Done — {scores.Count} scored");

        // ── Build result ──────────────────────────────────────────────────────
        var topConfigs = scores.Take(10).Select(s =>
            unique.First(c => c.Raw == s.Config)).ToList();

        var stats = new PipelineStats(
            Fetched: parsed.Count,
            Deduped: unique.Count,
            Healthy: healthyCount,
            Scored:  scores.Count,
            Sources: fetchResults.Count(r => r.Success)
        );

        return new PipelineResult(unique, scores, topConfigs, stats);
    }

    private static void Report(ProgressCallback? cb, string stage, int current, int total, string msg)
        => cb?.Invoke(stage, current, total, msg);
}
