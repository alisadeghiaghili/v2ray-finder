# Interruption & Token Guide

## Token Input Methods

### 1. Environment Variable (Recommended)

**Most secure** — token never exposed in process list or history.

```bash
export GITHUB_TOKEN="ghp_yourTokenHere"
v2ray-finder -s
```

### 2. Interactive Prompt (Secure)

Use `--prompt-token` flag for masked input:

```bash
v2ray-finder --prompt-token -s -o servers.txt
# or
v2ray-finder-rich --prompt-token -s
```

In interactive mode (no args), you'll be automatically prompted if no token is found.

### 3. CLI Argument (Not Recommended)

```bash
v2ray-finder -t "ghp_yourToken" -s  # ⚠️ INSECURE - visible in process list
```

**Warning:** Token appears in:
- Shell history (`~/.bash_history`)
- Process listings (`ps aux`)
- System logs

---

## Graceful Interruption

### How It Works

**Press `Ctrl+C` at any time** during fetch operations to:
1. Stop ongoing requests immediately
2. Save all servers collected so far
3. Display statistics for partial results
4. Exit cleanly with code `130` (SIGINT)

### Examples

#### CLI (plain)

```bash
v2ray-finder -s -o servers.txt
# ... fetching ...
# Press Ctrl+C

[!] Interrupted by user. Saving partial results...

[✓] Saved 47 servers to v2ray_servers_partial.txt
    You can resume or use these servers.

Total servers: 47
By protocol:
  vmess: 23
  vless: 15
  trojan: 9
```

#### Rich CLI

```bash
v2ray-finder-rich -s
# ... fetching ...
# Press Ctrl+C

⚠ Interrupted by user
Saving partial results...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00

✓ Saved 47 servers to v2ray_servers_partial.txt
```

### Interactive Mode

In interactive menu:
- `Ctrl+C` during fetch → saves partial + shows stats
- `Ctrl+C` at menu → exits gracefully

```bash
v2ray-finder-rich

Options:
1. Quick fetch (known sources only)
2. Full fetch (sources + GitHub search)
3. Fetch with health checking
# Select 2, then press Ctrl+C during fetch

! Interrupted - found 34 servers so far
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
✓ Saved 34 servers to v2ray_servers_partial.txt
```

---

## Partial Results Behavior

### File Naming

| Context | Output File |
|---------|-------------|
| CLI with `-o` flag | Uses your specified filename |
| CLI without `-o` | `v2ray_servers_partial.txt` |
| Health check mode | `v2ray_servers_partial_health.txt` |
| Rich CLI | `v2ray_servers_partial.txt` |

### What Gets Saved

- **Known sources fetch**: All servers from completed sources
- **GitHub search**: Repos processed before interrupt + their servers
- **Health check**: Servers checked before interrupt (with health data)

### Resume Strategy

```bash
# Check what you got
wc -l v2ray_servers_partial.txt
# 47 v2ray_servers_partial.txt

# Use partial results
cat v2ray_servers_partial.txt

# Or continue with a new full fetch
v2ray-finder -s -o servers_complete.txt
```

---

## Exit Codes

| Code | Meaning | Cause |
|------|---------|-------|
| `0` | Success | Normal completion |
| `1` | Error | Rate limit, auth error, or unexpected exception |
| `130` | Interrupted | User pressed Ctrl+C (SIGINT) |

### Handling in Scripts

```bash
#!/bin/bash

v2ray-finder -s -o servers.txt
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Success!"
    # Process servers.txt
elif [ $exit_code -eq 130 ]; then
    echo "Interrupted - using partial results"
    # Process v2ray_servers_partial.txt
else
    echo "Error occurred"
    exit 1
fi
```

---

## Signal Handling Details

### What Happens on SIGINT

1. **Signal caught** by `signal_handler()`
2. **Global flag set** (`_interrupted = True`)
3. **Current operation stops** gracefully
4. **Partial servers saved** to disk
5. **Statistics printed** for saved data
6. **Process exits** with code `130`

### What Does NOT Happen

- ❌ Abrupt termination (no data loss)
- ❌ Corrupted output files
- ❌ Dangling network connections
- ❌ Incomplete JSON/config writes

### Technical Implementation

```python
# Global state tracking
_interrupted = False
_partial_servers = []

def signal_handler(signum, frame):
    global _interrupted
    _interrupted = True
    print("\n[!] Interrupted by user...")

# Register at startup
signal.signal(signal.SIGINT, signal_handler)

# Check during long operations
try:
    for repo in repos:
        if _interrupted:
            break
        # ... fetch ...
        _partial_servers.append(servers)
except KeyboardInterrupt:
    save_partial_results(_partial_servers)
```

---

## Best Practices

### ✅ Do

- Use `--prompt-token` or `GITHUB_TOKEN` env var
- Press Ctrl+C if fetch is taking too long
- Check partial results file after interruption
- Use `--limit` to control fetch size upfront

### ❌ Don't

- Don't use `-t` flag for tokens (insecure)
- Don't kill process with `kill -9` (no cleanup)
- Don't ignore partial results (they're valid!)
- Don't spam Ctrl+C (once is enough)

---

## Troubleshooting

### Partial File Not Created

**Cause:** Interrupted before any servers were fetched.

**Solution:** Wait a few seconds before interrupting, or check if sources are reachable.

### Token Not Recognized After Prompt

**Cause:** Invalid token format or whitespace.

**Solution:**
```bash
# Verify token format
echo $GITHUB_TOKEN | wc -c  # Should be 40+ chars

# Re-export cleanly
export GITHUB_TOKEN="ghp_..."
```

### Exit Code 1 Instead of 130

**Cause:** Exception occurred before interrupt was caught.

**Solution:** Check error message — might be rate limit or network issue unrelated to interrupt.

---

## Examples by Use Case

### Quick Test Without Token

```bash
v2ray-finder -o test.txt
# Press Ctrl+C after 5 seconds
# Uses partial results — good for testing
```

### Production Fetch with Token

```bash
export GITHUB_TOKEN="ghp_..."
v2ray-finder -s -c --min-quality 60 -o production.txt
# Let it complete or interrupt safely
```

### Interactive Exploration

```bash
v2ray-finder-rich
# Prompted for token automatically
# Try options 1-3, interrupt if needed
# Option 5 to save results
```

### CI/CD Pipeline

```bash
#!/bin/bash
set -e

# Timeout after 2 minutes
timeout 120 v2ray-finder -s -o servers.txt || {
    if [ $? -eq 124 ]; then
        echo "Timeout - using partial results"
        mv v2ray_servers_partial.txt servers.txt
    fi
}

# Validate output
if [ ! -s servers.txt ]; then
    echo "No servers fetched"
    exit 1
fi
```
