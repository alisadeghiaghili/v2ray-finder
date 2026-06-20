using System.Text;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using V2RayFinder.Core.Models;

namespace V2RayFinder.Core;

/// <summary>
/// Fetches subscription URLs concurrently with retry logic.
/// Equivalent to Python's AsyncFetcher.
/// </summary>
public sealed class SubscriptionFetcher : IDisposable
{
    private readonly HttpClient _http;
    private readonly ILogger<SubscriptionFetcher> _logger;
    private readonly int _maxConcurrency;
    private readonly int _maxRetries;
    private readonly TimeSpan _timeout;

    public SubscriptionFetcher(
        ILogger<SubscriptionFetcher>? logger = null,
        int maxConcurrency = 10,
        int maxRetries = 3,
        TimeSpan? timeout = null)
    {
        _logger = logger ?? NullLogger<SubscriptionFetcher>.Instance;
        _maxConcurrency = maxConcurrency;
        _maxRetries = maxRetries;
        _timeout = timeout ?? TimeSpan.FromSeconds(15);

        _http = new HttpClient
        {
            Timeout = _timeout,
            DefaultRequestHeaders =
            {
                { "User-Agent", "V2RayFinder/1.0 (https://github.com)" }
            }
        };
    }

    /// <summary>
    /// Fetches all given URLs concurrently, respecting concurrency limit.
    /// </summary>
    public async Task<IReadOnlyList<FetchResult>> FetchAllAsync(
        IEnumerable<string> urls,
        CancellationToken ct = default)
    {
        var semaphore = new SemaphoreSlim(_maxConcurrency, _maxConcurrency);
        var tasks = urls.Select(url => FetchWithSemaphoreAsync(url, semaphore, ct));
        var results = await Task.WhenAll(tasks);
        return results;
    }

    private async Task<FetchResult> FetchWithSemaphoreAsync(
        string url, SemaphoreSlim semaphore, CancellationToken ct)
    {
        await semaphore.WaitAsync(ct);
        try
        {
            return await FetchWithRetryAsync(url, ct);
        }
        finally
        {
            semaphore.Release();
        }
    }

    private async Task<FetchResult> FetchWithRetryAsync(string url, CancellationToken ct)
    {
        StructuredError? lastError = null;
        var delay = TimeSpan.FromSeconds(1);

        for (int attempt = 0; attempt <= _maxRetries; attempt++)
        {
            if (attempt > 0)
            {
                _logger.LogDebug("Retry {attempt}/{max} for {url}", attempt, _maxRetries, url);
                await Task.Delay(delay, ct);
                delay *= 2; // exponential backoff
            }

            try
            {
                var response = await _http.GetAsync(url, ct);

                if (!response.IsSuccessStatusCode)
                {
                    var code = (int)response.StatusCode;
                    lastError = new StructuredError(
                        "network",
                        $"http_{code}",
                        $"HTTP {code} from {url}",
                        Retryable: code >= 500
                    );
                    if (code < 500) break; // 4xx → no retry
                    continue;
                }

                var body = await ReadBodyAsync(response);
                var lines = ParseLines(body);

                _logger.LogDebug("Fetched {count} lines from {url}", lines.Count, url);
                return new FetchResult(url, true, lines);
            }
            catch (TaskCanceledException ex) when (!ct.IsCancellationRequested)
            {
                lastError = new StructuredError("network", "timeout", ex.Message, true);
            }
            catch (HttpRequestException ex)
            {
                var kind = ex.Message.Contains("Name or service not known") ||
                           ex.Message.Contains("No such host") ? "dns" : "connection";
                lastError = new StructuredError("network", kind, ex.Message, kind == "dns" ? false : true);
                if (kind == "dns") break; // DNS failure → no retry
            }
            catch (Exception ex)
            {
                lastError = new StructuredError("unknown", "exception", ex.Message, false);
                break;
            }
        }

        _logger.LogWarning("Failed to fetch {url}: {error}", url, lastError?.Message);
        return new FetchResult(url, false, Array.Empty<string>(), lastError);
    }

    private static async Task<string> ReadBodyAsync(HttpResponseMessage response)
    {
        var bytes = await response.Content.ReadAsByteArrayAsync();

        // Try to decode as UTF-8; if it looks like base64, decode it
        var text = Encoding.UTF8.GetString(bytes).Trim();

        // If entire body is base64-encoded subscription, decode it
        if (IsBase64(text))
        {
            try
            {
                var decoded = Encoding.UTF8.GetString(Convert.FromBase64String(
                    text.PadRight(text.Length + (4 - text.Length % 4) % 4, '=')));
                return decoded;
            }
            catch { /* fall through */ }
        }

        return text;
    }

    private static bool IsBase64(string s)
    {
        if (s.Length < 20) return false;
        // If it contains no vmess/vless/trojan/ss prefixes but is pure base64 chars
        if (s.Contains("vmess://") || s.Contains("vless://") ||
            s.Contains("trojan://") || s.Contains("ss://"))
            return false;

        return System.Text.RegularExpressions.Regex.IsMatch(s, @"^[A-Za-z0-9+/\r\n]+=*$");
    }

    private static List<string> ParseLines(string body) =>
        body.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .ToList();

    public void Dispose() => _http.Dispose();
}
