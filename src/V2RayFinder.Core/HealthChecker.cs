using System.Diagnostics;
using System.Net.Sockets;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using V2RayFinder.Core.Models;

namespace V2RayFinder.Core;

/// <summary>
/// Layer-1 (TCP) and Layer-2 (HTTP probe) health checking.
/// Equivalent to Python's health_checker module.
/// </summary>
public sealed class HealthChecker
{
    private readonly ILogger<HealthChecker> _logger;
    private readonly TimeSpan _tcpTimeout;
    private readonly int _concurrency;

    public HealthChecker(
        ILogger<HealthChecker>? logger = null,
        TimeSpan? tcpTimeout = null,
        int concurrency = 50)
    {
        _logger = logger ?? NullLogger<HealthChecker>.Instance;
        _tcpTimeout = tcpTimeout ?? TimeSpan.FromSeconds(5);
        _concurrency = concurrency;
    }

    /// <summary>
    /// Check all configs concurrently and return health results.
    /// </summary>
    public async Task<IReadOnlyList<HealthResult>> CheckAllAsync(
        IEnumerable<V2RayConfig> configs,
        CancellationToken ct = default)
    {
        var semaphore = new SemaphoreSlim(_concurrency, _concurrency);
        var tasks = configs.Select(c => CheckWithSemaphoreAsync(c, semaphore, ct));
        return await Task.WhenAll(tasks);
    }

    private async Task<HealthResult> CheckWithSemaphoreAsync(
        V2RayConfig config, SemaphoreSlim semaphore, CancellationToken ct)
    {
        await semaphore.WaitAsync(ct);
        try { return await CheckTcpAsync(config, ct); }
        finally { semaphore.Release(); }
    }

    private async Task<HealthResult> CheckTcpAsync(V2RayConfig config, CancellationToken ct)
    {
        if (config.Host is null || config.Port is null)
        {
            return new HealthResult(config.Raw, false, 0, HealthLayer.None, "No host/port");
        }

        var sw = Stopwatch.StartNew();
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(_tcpTimeout);

        try
        {
            using var tcp = new TcpClient();
            await tcp.ConnectAsync(config.Host, config.Port.Value, cts.Token);
            sw.Stop();
            _logger.LogDebug("TCP OK {host}:{port} in {ms}ms", config.Host, config.Port, sw.ElapsedMilliseconds);
            return new HealthResult(config.Raw, true, sw.Elapsed.TotalMilliseconds, HealthLayer.Tcp);
        }
        catch (OperationCanceledException)
        {
            return new HealthResult(config.Raw, false, _tcpTimeout.TotalMilliseconds, HealthLayer.None, "Timeout");
        }
        catch (Exception ex)
        {
            return new HealthResult(config.Raw, false, sw.Elapsed.TotalMilliseconds, HealthLayer.None, ex.Message);
        }
    }
}
