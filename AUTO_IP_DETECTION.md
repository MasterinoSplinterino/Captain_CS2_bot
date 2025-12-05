# Automatic Public IP Detection - Simplified Architecture

## TL;DR
CS2 server **does not require PUBLIC_IP** to function. The upstream image only uses it for console logging. We disabled auto-detection (`PUBLIC_IP_FETCH=0`) and use a separate detector container purely for bot display purposes.

## Architecture

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────┐
│  ip-detector    │──────▶│  shared volume   │◀──────│     bot     │
│  (sidecar)      │ write │ /shared/         │ read  │  (display)  │
│  Alpine + curl  │       │ public_ip.txt    │       │  status cmd │
└─────────────────┘       └──────────────────┘       └─────────────┘
                                                             
                          ┌──────────────────┐
                          │   cs2-server     │
                          │ PUBLIC_IP_FETCH=0│ (no IP needed)
                          │  runs normally   │
                          └──────────────────┘
```

## Components

### 1. IP Detector Container
**Purpose**: Continuously polls public IP and writes to shared volume  
**Image**: Alpine 3.20 + bash/curl/bind-tools  
**Refresh**: Every 60 seconds  
**Output**: `/shared/public_ip.txt` (plain text) and `public_ip.json` (with timestamp)  
**Failure**: Silent - bot falls back to domain/manual IP

### 2. CS2 Server Container
**Entrypoint**: `scripts/public_ip_entrypoint.sh`  
**Environment**: `PUBLIC_IP_FETCH=0` (disables upstream auto-detection)  
**Behavior**: Starts immediately without IP validation  
**Logging**: No more "Cannot retrieve your public IP address" errors

### 3. Bot Container
**Config**: `bot/bot_config.py`  
**Priority**: Domain → Cache → Manual IP → HTTP fallback  
**Command**: `!status` reads `/shared/public_ip.txt` for display

## Why This Works

1. **CS2 server doesn't need PUBLIC_IP**: Only used for console log message "Starting server on X.X.X.X:27015"
2. **No upstream modification**: Set `PUBLIC_IP_FETCH=0` instead of patching install_docker.sh
3. **Bot reads cache**: Players see correct IP in status command
4. **Fail-safe**: If detector fails, server still runs, bot uses fallback chain

## Configuration

### docker-compose.yml
```yaml
services:
  public-ip:
    build: ./ip-detector
    volumes:
      - public-ip-cache:/shared

  cs2:
    depends_on:
      - public-ip
    environment:
      PUBLIC_IP_FETCH: "0"  # Disable auto-detection
    volumes:
      - public-ip-cache:/shared:ro
      - ./scripts:/scripts:ro
    entrypoint: ["/bin/bash", "/scripts/public_ip_entrypoint.sh"]

  bot:
    volumes:
      - public-ip-cache:/shared:ro
    environment:
      PUBLIC_IP_FILE: /shared/public_ip.txt

volumes:
  public-ip-cache:
```

## Testing

```bash
# Check detector is running
docker logs public-ip --tail 20

# Verify cache file exists
docker exec cs2-server cat /shared/public_ip.txt

# Check bot reads it
docker exec cs2-bot python -c "from bot_config import read_public_ip_from_cache; print(read_public_ip_from_cache())"

# Verify server started without IP errors
docker logs cs2-server | grep -E "PUBLIC_IP|Cannot retrieve"
# Should see: "[cs2-entrypoint] Disabling PUBLIC_IP auto-detection"
# Should NOT see: "ERROR: Cannot retrieve your public IP address"
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Server loop "Cannot retrieve..." | `PUBLIC_IP_FETCH` not set | Check env var in docker-compose.yml |
| Bot shows wrong IP | Cache file empty/outdated | Check `docker logs public-ip` |
| Detector fails silently | Network issues | Check logs for curl/dig errors |
| Cache file missing | Volume mount issue | Verify `public-ip-cache` volume exists |

## Fallback Chain

Bot connection address priority:
1. **CS2_DOMAIN** (if set) - best for DNS
2. **Cached IP** (`/shared/public_ip.txt`) - preferred
3. **CS2_IP** (manual) - static configuration
4. **HTTP detection** - last resort (blocks bot startup)

## References

- CS2 server docs: https://github.com/kus/cs2-modded-server
- Environment variables: IP is optional ("Not required. Allows the server IP to be set...")
- `PUBLIC_IP_FETCH=0` disables install_docker.sh IP detection logic
