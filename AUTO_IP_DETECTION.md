# Automatic Public IP Detection - Simplified Architecture

## TL;DR
CS2 upstream requires `PUBLIC_IP` variable. We set it to `0.0.0.0` in docker-compose (for console log only). Bot displays **real IP** from detector cache.

## Architecture

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────┐
│  ip-detector    │──────▶│  shared volume   │◀──────│     bot     │
│  (every 60s)    │ write │ /shared/         │ read  │  (display)  │
│                 │       │ public_ip.txt    │       │  !status    │
└─────────────────┘       └──────────────────┘       └─────────────┘
                                                      Shows: 79.137.206.223
                          
                          ┌──────────────────┐
                          │   cs2-server     │
                          │ PUBLIC_IP=0.0.0.0│ ✅ No restart loop
                          └──────────────────┘
                          Console: "Starting server on 0.0.0.0:27015"
```

## Components

### 1. IP Detector Container
**Purpose**: Continuously polls public IP and writes to shared volume  
**Image**: Alpine 3.20 + bash/curl/bind-tools  
**Refresh**: Every 60 seconds  
**Output**: `/shared/public_ip.txt` (79.137.206.223)  
**Failure**: Silent - writes nothing, bot uses fallback

### 2. CS2 Server Container
**Environment**: `PUBLIC_IP=0.0.0.0` (dummy value to satisfy upstream check)  
**Volume**: `/shared:ro` (reads real IP, but doesn't use it)  
**Result**: Upstream `install_docker.sh` sees PUBLIC_IP set → doesn't fail → server starts

### 3. Bot Container
**Config**: `bot/bot_config.py`  
**Read**: `/shared/public_ip.txt` → validates IPv4 → displays in `!status`  
**Priority**: Domain → Cache → Manual IP → HTTP fallback

## Why This Works

1. **Upstream requires PUBLIC_IP**: `install_docker.sh` line 73-76 exits if `PUBLIC_IP` is empty
2. **0.0.0.0 satisfies check**: Script doesn't crash, server starts normally
3. **Console log doesn't matter**: Shows "Starting server on 0.0.0.0:27015" (not used by players)
4. **Bot shows real IP**: Reads cache directly, displays 79.137.206.223 to players
5. **No entrypoint scripts needed**: Simple env var, no bash wrappers

## Configuration

### docker-compose.yml
```yaml
services:
  public-ip:
    build: ./ip-detector
    volumes:
      - public-ip-cache:/shared

  cs2:
    environment:
      PUBLIC_IP: "0.0.0.0"  # Dummy IP for console log
      PUBLIC_IP_FILE: /shared/public_ip.txt
    volumes:
      - public-ip-cache:/shared:ro

  bot:
    environment:
      PUBLIC_IP_FILE: /shared/public_ip.txt
    volumes:
      - public-ip-cache:/shared:ro

volumes:
  public-ip-cache:
```

## Testing

```bash
# Check no restart loop
docker logs cs2-server | grep -c "ERROR: Cannot retrieve"
# Should be: 0

# Verify console shows dummy IP (expected)
docker logs cs2-server | grep "Starting server"
# Starting server on 0.0.0.0:27015

# Check detector writes real IP
docker exec cs2-server cat /shared/public_ip.txt
# 79.137.206.223

# Verify bot shows real IP
# In Telegram: /status
# Should display: 79.137.206.223:27015
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Server restart loop | PUBLIC_IP not set in compose | Add `PUBLIC_IP: "0.0.0.0"` to environment |
| Bot shows 0.0.0.0 | Cache empty, bot reads CS2_IP fallback | Wait for detector, check `docker logs public-ip` |
| Console shows 0.0.0.0 | Expected behavior | Ignore console log, players use bot's real IP |

## Benefits

✅ **Simple**: Just one env var `PUBLIC_IP=0.0.0.0`  
✅ **No scripts**: No entrypoint wrappers, no bash logic  
✅ **Reliable**: Server never crashes from IP detection  
✅ **Accurate**: Players see real IP from bot  
✅ **Maintainable**: Compatible with upstream updates

## References

- Upstream check: https://github.com/kus/cs2-modded-server/blob/master/install_docker.sh#L73-L76
- Bot config: `bot/bot_config.py` → `read_public_ip_from_cache()`
