using System.Diagnostics;
using V2RayFinder.Core;
using V2RayFinder.Core.Models;

// ── Argument parsing ─────────────────────────────────────────────────────────

var _args = Args.Parse(Environment.GetCommandLineArgs()[1..]);

if (_args.ShowHelp)
{
    PrintHelp();
    return 0;
}

// ── Setup cancellation (Ctrl+C) ───────────────────────────────────────────────
using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) =>
{
    e.Cancel = true;
    Console.WriteLine("\n[!] Stopping... (saving partial results)");
    cts.Cancel();
};

// ── Run pipeline ──────────────────────────────────────────────────────────────

Console.WriteLine("╔══════════════════════════════════════════╗");
Console.WriteLine("║        V2Ray Finder  (.NET Edition)      ║");
Console.WriteLine("╚══════════════════════════════════════════╝");
Console.WriteLine();

var sw = Stopwatch.StartNew();

var pipeline = new Pipeline(
    checkHealth:       _args.CheckHealth,
    fetchConcurrency:  _args.Concurrency,
    limit:             _args.Limit,
    fetchTimeout:      TimeSpan.FromSeconds(_args.Timeout)
);

PipelineResult result;
try
{
    result = await pipeline.RunAsync(cts.Token, OnProgress);
}
catch (OperationCanceledException)
{
    Console.WriteLine("\n[!] Cancelled.");
    return 1;
}

sw.Stop();

// ── Print summary ─────────────────────────────────────────────────────────────

Console.WriteLine();
Console.WriteLine("── Results ────────────────────────────────────────────────");
Console.WriteLine($"  Sources OK    : {result.Stats.Sources}");
Console.WriteLine($"  Fetched       : {result.Stats.Fetched}");
Console.WriteLine($"  Unique        : {result.Stats.Deduped}");
if (_args.CheckHealth)
    Console.WriteLine($"  Healthy       : {result.Stats.Healthy}");
Console.WriteLine($"  Scored        : {result.Stats.Scored}");
Console.WriteLine($"  Elapsed       : {sw.Elapsed:mm\\:ss\\.ff}");
Console.WriteLine();

// Protocol breakdown
var byProtocol = result.Configs
    .GroupBy(c => c.Protocol)
    .OrderByDescending(g => g.Count())
    .Select(g => $"  {g.Key,-14}: {g.Count()}");
Console.WriteLine("── Protocol Breakdown ─────────────────────────────────────");
foreach (var line in byProtocol) Console.WriteLine(line);
Console.WriteLine();

// Top 10 configs table
if (result.Scores.Count > 0)
{
    Console.WriteLine("── Top Configs ─────────────────────────────────────────────");
    Console.WriteLine($"  {"#",-4} {"Grade",-6} {"Score",-7} {"Proto",-12} {"Latency",-10} Config");
    Console.WriteLine($"  {new string('-', 80)}");

    int n = Math.Min(_args.TopN, result.Scores.Count);
    for (int i = 0; i < n; i++)
    {
        var s = result.Scores[i];
        var proto = s.Protocol.ToString()[..Math.Min(11, s.Protocol.ToString().Length)];
        var latency = s.LatencyMs > 0 ? $"{s.LatencyMs:F0}ms" : "—";
        var configPreview = s.Config.Length > 45 ? s.Config[..45] + "…" : s.Config;
        Console.WriteLine($"  {i + 1,-4} {s.Grade,-6} {s.Total:F3,-7} {proto,-12} {latency,-10} {configPreview}");
    }
    Console.WriteLine();
}

// Save to file
if (_args.OutputFile != null)
{
    var lines = result.Scores.Select(s => s.Config).ToList();
    await File.WriteAllLinesAsync(_args.OutputFile, lines, cts.Token);
    Console.WriteLine($"[✓] Saved {lines.Count} configs to {_args.OutputFile}");
}

return 0;

// ── Helper methods ────────────────────────────────────────────────────────────

static void OnProgress(string stage, int current, int total, string message)
{
    var icon = stage switch
    {
        "fetch"  => "⬇",
        "parse"  => "🔍",
        "dedup"  => "♻",
        "health" => "🏥",
        "score"  => "📊",
        _        => "•"
    };
    if (total > 0)
        Console.Write($"\r  {icon} [{stage.ToUpper(),-6}] {current}/{total}  {message,-40}");
    else
        Console.WriteLine($"  {icon} [{stage.ToUpper(),-6}] {message}");
}

static void PrintHelp()
{
    Console.WriteLine("""
    V2Ray Finder (.NET Edition)

    Usage: v2ray-finder [options]

    Options:
      -o, --output <file>    Save configs to file
      -c, --check-health     Enable TCP health checking
      -l, --limit <n>        Cap configs after dedup (default: 0 = unlimited)
      -n, --top <n>          Number of top configs to display (default: 10)
      -j, --concurrency <n>  Fetch concurrency (default: 10)
          --timeout <sec>    HTTP timeout in seconds (default: 15)
      -h, --help             Show this help

    Examples:
      v2ray-finder -o servers.txt
      v2ray-finder -c -l 200 -o healthy.txt
      v2ray-finder --check-health --top 20 -o out.txt
    """);
}

// ── Argument record ───────────────────────────────────────────────────────────

record Args(
    bool ShowHelp,
    bool CheckHealth,
    string? OutputFile,
    int Limit,
    int TopN,
    int Concurrency,
    int Timeout)
{
    public static Args Parse(string[] argv)
    {
        bool help = false, health = false;
        string? output = null;
        int limit = 0, topN = 10, concurrency = 10, timeout = 15;

        for (int i = 0; i < argv.Length; i++)
        {
            switch (argv[i])
            {
                case "-h": case "--help":        help = true; break;
                case "-c": case "--check-health": health = true; break;
                case "-o": case "--output":       output = argv[++i]; break;
                case "-l": case "--limit":        limit = int.Parse(argv[++i]); break;
                case "-n": case "--top":          topN = int.Parse(argv[++i]); break;
                case "-j": case "--concurrency":  concurrency = int.Parse(argv[++i]); break;
                case "--timeout":                 timeout = int.Parse(argv[++i]); break;
            }
        }

        return new Args(help, health, output, limit, topN, concurrency, timeout);
    }
}
