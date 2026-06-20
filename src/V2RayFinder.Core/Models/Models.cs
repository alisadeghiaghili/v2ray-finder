namespace V2RayFinder.Core.Models;

// ── Protocol types ──────────────────────────────────────────────────────────

public enum V2RayProtocol { Vmess, Vless, Trojan, Shadowsocks, Unknown }

public record V2RayConfig(
    string Raw,
    V2RayProtocol Protocol,
    string? Host,
    int? Port,
    string Fingerprint   // SHA-256 of Raw, used for dedup
);

// ── Result<T, E> monad (like Python's Result) ───────────────────────────────

public readonly struct Result<T, E>
{
    private readonly T? _value;
    private readonly E? _error;
    public bool IsOk { get; }

    private Result(T value) { _value = value; IsOk = true; _error = default; }
    private Result(E error) { _error = error; IsOk = false; _value = default; }

    public static Result<T, E> Ok(T value) => new(value);
    public static Result<T, E> Err(E error) => new(error);

    public T Unwrap() => IsOk ? _value! : throw new InvalidOperationException($"Result is error: {_error}");
    public E Error => IsOk ? throw new InvalidOperationException("Result is Ok") : _error!;
    public T UnwrapOr(T fallback) => IsOk ? _value! : fallback;
}

// ── Fetch result ─────────────────────────────────────────────────────────────

public record StructuredError(
    string Category,   // "network" | "parse" | "auth" | "rate_limit"
    string Kind,       // "timeout" | "dns" | "http_4xx" | ...
    string Message,
    bool Retryable
);

public record FetchResult(
    string Url,
    bool Success,
    IReadOnlyList<string> RawLines,
    StructuredError? StructuredError = null
);

// ── Health check ─────────────────────────────────────────────────────────────

public enum HealthLayer { None, Tcp, Http }

public record HealthResult(
    string Config,
    bool IsHealthy,
    double LatencyMs,
    HealthLayer Layer,
    string? Error = null
);

// ── Scoring ──────────────────────────────────────────────────────────────────

public record ConfigScore(
    string Config,
    V2RayProtocol Protocol,
    double Total,
    string Grade,
    double LatencyMs,
    string? Source = null
)
{
    public static string CalculateGrade(double score) => score switch
    {
        >= 0.85 => "A",
        >= 0.70 => "B",
        >= 0.55 => "C",
        >= 0.40 => "D",
        _ => "F"
    };
}

// ── Pipeline result ───────────────────────────────────────────────────────────

public record PipelineStats(
    int Fetched,
    int Deduped,
    int Healthy,
    int Scored,
    int Sources
);

public record PipelineResult(
    IReadOnlyList<V2RayConfig> Configs,
    IReadOnlyList<ConfigScore> Scores,
    IReadOnlyList<V2RayConfig> TopConfigs,
    PipelineStats Stats
);
