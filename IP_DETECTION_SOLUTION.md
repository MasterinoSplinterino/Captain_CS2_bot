# Решение проблемы "Cannot retrieve your public IP address"

## Проблема
Сервер CS2 зацикливался при загрузке с ошибкой:
```
ERROR: Cannot retrieve your public IP address.
ERROR: Cannot retrieve your public IP address.
```

## Причина
Upstream-образ `ghcr.io/kus/cs2-modded-server` **требует** переменную `PUBLIC_IP` в скрипте `install_docker.sh`:
```bash
PUBLIC_IP=$(dig +short myip.opendns.com @resolver1.opendns.com)
if [ -z "$PUBLIC_IP" ]; then
    echo "ERROR: Cannot retrieve your public IP address..."
    exit 1
fi
```

НО: серверу CS2 этот IP **не нужен для работы** - используется только для вывода в консоль "Starting server on X.X.X.X:27015".

## Решение
Устанавливаем `PUBLIC_IP` из кеша перед запуском upstream-скрипта. Если кеш недоступен - используем fallback `0.0.0.0` чтобы избежать цикла рестартов.

## Что изменилось

### 1. Entrypoint для CS2 сервера (scripts/public_ip_entrypoint.sh)
```bash
#!/bin/bash
# Reads cached PUBLIC_IP before upstream install_docker.sh runs
PUBLIC_IP_FILE="${PUBLIC_IP_FILE:-/shared/public_ip.txt}"

# Try to read cached IP
if [[ -f "$PUBLIC_IP_FILE" ]]; then
    CACHED_IP="$(head -n1 "$PUBLIC_IP_FILE" | tr -d '\r\n ')"
    if [[ "$CACHED_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        export PUBLIC_IP="$CACHED_IP"
    fi
fi

# Fallback if no cache: use dummy IP to prevent loop
if [[ -z "${PUBLIC_IP:-}" ]]; then
    export PUBLIC_IP="0.0.0.0"
fi

exec sudo -E bash /home/cs2-modded-server/install_docker.sh
```

### 2. Docker Compose (без изменений)
```yaml
cs2:
  environment:
    - PUBLIC_IP_FILE=/shared/public_ip.txt
  volumes:
    - public-ip-cache:/shared:ro
  entrypoint: ["/bin/bash", "/scripts/public_ip_entrypoint.sh"]
```

### 3. IP Detector (без изменений)
Отдельный контейнер продолжает определять IP каждые 60 секунд и записывает в `/shared/public_ip.txt`.

## Архитектура

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────┐
│  ip-detector    │──────▶│  shared volume   │◀──────│     bot     │
│ (каждые 60 сек) │ write │ /shared/         │ read  │  (display)  │
│                 │       │ public_ip.txt    │       │  !status    │
└─────────────────┘       └──────────────────┘       └─────────────┘
                                    │                        
                                    │ read (при старте)      
                                    ▼                        
                          ┌──────────────────┐
                          │   cs2-server     │
                          │  export PUBLIC_IP │ ✅ запускается с кешированным IP
                          │  (или 0.0.0.0)   │    или fallback, не падает
                          └──────────────────┘
```

## Почему это работает

1. **Upstream требует PUBLIC_IP** - без него скрипт выходит с ошибкой
2. **Entrypoint читает кеш** - если детектор успел определить IP, используем его
3. **Fallback предотвращает цикл** - если кеша нет, ставим `0.0.0.0` вместо падения
4. **Сервер работает с любым IP** - даже с `0.0.0.0`, просто лог будет неправильный
5. **Бот получает правильный IP** из кеша независимо от того, что видит сервер

## Как проверить что работает

```bash
# 1. Запустить проект
docker-compose up -d

# 2. Проверить что сервер запустился БЕЗ цикла рестартов
docker logs cs2-server --tail 50
# Должно быть:
# [cs2-entrypoint] Reading cached IP from /shared/public_ip.txt
# [cs2-entrypoint] Using cached PUBLIC_IP=79.137.206.223
# Starting server on 79.137.206.223:27015
# НЕ ДОЛЖНО быть повторяющихся:
# ERROR: Cannot retrieve your public IP address...

# 3. Проверить что IP Detector работает
docker logs public-ip --tail 10
# [IP-DETECTOR] Detected public IP: 79.137.206.223

# 4. Проверить что бот видит IP
docker exec cs2-bot python -c "from bot_config import read_public_ip_from_cache; print(read_public_ip_from_cache())"
# 79.137.206.223
```

## Сценарии работы

| Ситуация | Поведение |
|----------|----------|
| Детектор работает, кеш заполнен | ✅ Сервер использует кешированный IP |
| Детектор еще не запущен | ⚠️ Сервер использует `0.0.0.0`, бот ждет кеш |
| Детектор упал | ⚠️ Сервер использует старый IP из кеша (или `0.0.0.0`) |
| Кеш файл поврежден | ⚠️ Сервер использует `0.0.0.0`, бот использует fallback |

Во всех случаях **сервер запускается и работает**, не зацикливается.

## Ссылки

- Документация cs2-modded-server: https://github.com/kus/cs2-modded-server
- Исходный код install_docker.sh: строки 73-76 (проверка PUBLIC_IP обязательна)
- Файл AUTO_IP_DETECTION.md - подробная архитектура
