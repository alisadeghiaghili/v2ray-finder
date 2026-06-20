# V2Ray Finder — .NET Edition

Port of [v2ray-finder](https://github.com/alisadeghiaghili/v2ray-finder) in **C# / .NET 8**.

## ساختار پروژه

```
V2RayFinder/
├── src/
│   ├── V2RayFinder.Core/          # کتابخانه اصلی
│   │   ├── Models/Models.cs       # مدل‌ها (V2RayConfig, Result<T,E>, ...)
│   │   ├── ConfigParser.cs        # پارسر کانفیگ‌های V2Ray
│   │   ├── SubscriptionSources.cs # لیست منابع عمومی
│   │   ├── SubscriptionFetcher.cs # فچر async با retry و structured error
│   │   ├── HealthChecker.cs       # بررسی سلامت TCP
│   │   ├── ConfigScorer.cs        # امتیازدهی A–F
│   │   └── Pipeline.cs            # ارکستراتور اصلی
│   └── V2RayFinder.Cli/           # برنامه CLI
│       └── Program.cs
```

## معادل‌سازی با Python

| Python | C# |
|--------|-----|
| `Pipeline` | `Pipeline` |
| `AsyncFetcher` | `SubscriptionFetcher` |
| `HealthChecker` | `HealthChecker` |
| `ConfigScorer` | `ConfigScorer` |
| `StopController` | `CancellationToken` |
| `Result[T, E]` | `Result<T, E>` |
| `FetchResult.structured_error` | `FetchResult.StructuredError` |
| `PipelineResult` | `PipelineResult` |

## نصب و اجرا

```bash
# Build
dotnet build

# Run CLI
dotnet run --project src/V2RayFinder.Cli -- -o servers.txt
dotnet run --project src/V2RayFinder.Cli -- --check-health -l 200 -o healthy.txt
```

## استفاده از API

```csharp
using V2RayFinder.Core;

// ساده‌ترین حالت
var pipeline = new Pipeline(checkHealth: true);
var result = await pipeline.RunAsync();

Console.WriteLine($"Fetched: {result.Stats.Fetched}, Unique: {result.Stats.Deduped}");
foreach (var score in result.Scores.Take(10))
    Console.WriteLine($"{score.Grade}  {score.Total:F3}  {score.Config[..80]}");

// با cancellation
using var cts = new CancellationTokenSource();
var result = await pipeline.RunAsync(cts.Token, onProgress: (stage, cur, tot, msg) =>
    Console.WriteLine($"[{stage}] {cur}/{tot} {msg}"));

// ذخیره در فایل
await File.WriteAllLinesAsync("servers.txt", result.Scores.Select(s => s.Config));
```

## CLI Options

```
-o, --output <file>    ذخیره در فایل
-c, --check-health     بررسی TCP
-l, --limit <n>        حداکثر تعداد کانفیگ
-n, --top <n>          نمایش N کانفیگ برتر (default: 10)
-j, --concurrency <n>  همزمانی fetch (default: 10)
    --timeout <sec>    تایم‌اوت (default: 15)
-h, --help             راهنما
```
