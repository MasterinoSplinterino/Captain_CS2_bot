# Automatic Public IP Detection - Architecture

## TL;DR
CS2 upstream image **requires PUBLIC_IP** for install_docker.sh to start. We read it from a shared cache populated by a detector sidecar. If cache unavailable, use `0.0.0.0` fallback to prevent restart loops.

## Architecture

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────┐
│  ip-detector    │──────▶│  shared volume   │◀──────│     bot     │
│  (sidecar)      │ write │ /shared/         │ read  │  (display)  │
│  Alpine + curl  │       │ public_ip.txt    │       │  !status    │
└─────────────────┘       └──────────────────┘       └─────────────┘
                                    │                        
                                    │ read (at startup)      
                                    ▼                        
                          ┌──────────────────┐
                          │   cs2-server     │
                          │  export PUBLIC_IP │ ✅ starts with cached IP
                          │  (or 0.0.0.0)    │    or fallback, no crash
                          └──────────────────┘
```

## Components

### 1. IP Detector Container
**Purpose**: Continuously polls public IP and writes to shared volume  
**Image**: Alpine 3.20 + bash/curl/bind-tools  
**Refresh**: Every 60 seconds  
**Output**: `/shared/public_ip.txt` (plain text) and `public_ip.json` (with timestamp)  
**Failure**: Silent - writes nothing, consumers use fallback

### 2. CS2 Server Entrypoint
**Script**: `scripts/public_ip_entrypoint.sh`  
**Logic**: Reads `/shared/public_ip.txt` → validates IPv4 → exports `PUBLIC_IP`  
**Fallback**: If cache unavailable, exports `PUBLIC_IP=0.0.0.0`  
**Result**: Upstream `install_docker.sh` finds `PUBLIC_IP` set, skips dig check, starts server

### 3. Bot Container
**Config**: `bot/bot_config.py`  
**Priority**: Domain → Cache (`/shared/public_ip.txt`) → Manual IP → HTTP fallback  
**Command**: `!status` reads cache for display

## Why This Works

1. **Upstream requires PUBLIC_IP**: `install_docker.sh` line 73-76 checks `PUBLIC_IP` variable and exits if empty
2. **Cache provides real IP**: Detector runs independently, updates every 60s
3. **Fallback prevents loops**: If detector fails, `0.0.0.0` satisfies upstream check
4. **Server doesn't need real IP**: Only used for console log "Starting server on X.X.X.X:27015"
5. **Bot sees real IP**: Reads cache directly, shows correct IP to players

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
      PUBLIC_IP_FILE: /shared/public_ip.txt
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

## Flow

1. **Detector boots**: Immediately starts polling (first result ~2-5 seconds)
2. **CS2 starts**: Entrypoint reads `/shared/public_ip.txt`
3. **Cache found**: Exports `PUBLIC_IP=79.137.206.223`
4. **Cache missing**: Exports `PUBLIC_IP=0.0.0.0`
5. **Upstream runs**: Sees `PUBLIC_IP` set, skips dig, starts server
6. **Bot queries**: Reads cache for status display

## Testing

```bash
# Check detector is running
docker logs public-ip --tail 20

# Verify cache file exists
docker exec cs2-server cat /shared/public_ip.txt

# Check entrypoint behavior
docker logs cs2-server | grep -E "\[cs2-entrypoint\]"
# Should see: "Using cached PUBLIC_IP=79.137.206.223"
# OR: "WARNING: No cached IP found, using fallback PUBLIC_IP=0.0.0.0"

# Verify no restart loop
docker logs cs2-server | grep -c "ERROR: Cannot retrieve your public IP address"
# Should be: 0

# Check bot reads cache
docker exec cs2-bot python -c "from bot_config import read_public_ip_from_cache; print(read_public_ip_from_cache())"
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Server restart loop | Entrypoint not exporting PUBLIC_IP | Check entrypoint logs, verify cache mount |
| Server shows 0.0.0.0 in logs | Detector not writing cache | Check `docker logs public-ip` |
| Bot shows wrong IP | Cache file outdated | Restart detector container |
| Cache file missing | Volume mount issue | Verify `public-ip-cache` volume exists |

## Failure Scenarios

| Scenario | Behavior |
|----------|----------|
| Detector fails to start | ⚠️ CS2 uses `0.0.0.0`, bot uses fallback chain |
| Cache file invalid/empty | ⚠️ CS2 uses `0.0.0.0`, bot uses fallback chain |
| Network unavailable | ⚠️ Detector retries 6 endpoints, writes nothing, CS2 uses `0.0.0.0` |
| Cache outdated (IP changed) | ⚠️ CS2 shows old IP in logs, bot shows old IP (updates in 60s) |

**Critical**: Server **never crashes** due to IP issues - always falls back to `0.0.0.0`

## Fallback Chain

Bot connection address priority:
1. **CS2_DOMAIN** (if set) - best for DNS
2. **Cached IP** (`/shared/public_ip.txt`) - preferred
3. **CS2_IP** (manual) - static configuration
4. **HTTP detection** - last resort (blocks bot startup)

## References

- CS2 server repo: https://github.com/kus/cs2-modded-server
- install_docker.sh: Lines 73-76 require PUBLIC_IP (no disable flag exists)
- Upstream check: `if [ -z "$PUBLIC_IP" ]; then echo "ERROR: Cannot retrieve..."; exit 1; fi`
