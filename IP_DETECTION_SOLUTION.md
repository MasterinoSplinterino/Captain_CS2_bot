# Решение проблемы "Cannot retrieve your public IP address"

## Проблема
Сервер CS2 зацикливался при загрузке с ошибкой:
```
ERROR: Cannot retrieve your public IP address.
ERROR: Cannot retrieve your public IP address.
```

## Причина
Upstream-образ `ghcr.io/kus/cs2-modded-server` пытается автоматически определить PUBLIC_IP через скрипт `install_docker.sh`, но **серверу CS2 этот IP вообще не нужен для работы** - он используется только для вывода в консоль сообщения "Starting server on X.X.X.X:27015".

## Решение
Отключили автоматическое определение IP в upstream-скрипте через переменную окружения:

```bash
PUBLIC_IP_FETCH=0
```

## Что изменилось

### 1. Entrypoint для CS2 сервера (scripts/public_ip_entrypoint.sh)
```bash
#!/bin/bash
# Отключаем автоопределение IP в upstream
export PUBLIC_IP_FETCH=0
exec sudo -E bash /home/cs2-modded-server/install_docker.sh
```

### 2. Docker Compose (docker-compose.yml, docker-compose.prod.yml)
```yaml
cs2:
  environment:
    - PUBLIC_IP_FETCH=0  # Отключаем проверку IP
  entrypoint: ["/bin/bash", "/scripts/public_ip_entrypoint.sh"]
```

### 3. IP Detector (остается без изменений)
Отдельный контейнер продолжает определять IP каждые 60 секунд и записывает в `/shared/public_ip.txt` - этот IP используется **только ботом** для отображения в команде `!status`.

## Архитектура

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────┐
│  ip-detector    │──────▶│  shared volume   │◀──────│     bot     │
│   (для бота)    │ write │ /shared/         │ read  │  (display)  │
│                 │       │ public_ip.txt    │       │  !status    │
└─────────────────┘       └──────────────────┘       └─────────────┘
                                                             
                          ┌──────────────────┐
                          │   cs2-server     │
                          │ PUBLIC_IP_FETCH=0│ ✅ работает без IP
                          └──────────────────┘
```

## Почему это работает

1. **Сервер CS2 НЕ ТРЕБУЕТ PUBLIC_IP** для работы
   - Переменная используется только для лога "Starting server on X.X.X.X:27015"
   - Из документации: `IP` - "Not required. Allows the server IP to be set..."

2. **PUBLIC_IP_FETCH=0 отключает проверку** в install_docker.sh
   - Upstream-скрипт пропускает секцию определения IP
   - Сервер запускается сразу без задержек

3. **Бот получает IP из кеша** независимо от сервера
   - IP Detector работает параллельно
   - Бот читает `/shared/public_ip.txt` для команды `!status`
   - Если детектор упадет - бот использует fallback (domain → manual IP → HTTP)

## Как проверить что работает

```bash
# 1. Запустить проект
docker-compose up -d

# 2. Проверить что сервер запустился БЕЗ ошибок
docker logs cs2-server --tail 30
# Должно быть:
# [cs2-entrypoint] Disabling PUBLIC_IP auto-detection (PUBLIC_IP_FETCH=0)
# [cs2-entrypoint] Server will start without IP validation
# НЕ ДОЛЖНО БЫТЬ:
# ERROR: Cannot retrieve your public IP address

# 3. Проверить что IP Detector работает
docker logs public-ip --tail 10
# [IP-DETECTOR] Detected public IP: 79.137.206.223

# 4. Проверить что бот видит IP
docker exec cs2-bot python -c "from bot_config import read_public_ip_from_cache; print(read_public_ip_from_cache())"
# 79.137.206.223
```

## Ссылки

- Документация cs2-modded-server: https://github.com/kus/cs2-modded-server
- Переменные окружения: https://github.com/kus/cs2-modded-server#available-via-environment-variable-only
- Файл AUTO_IP_DETECTION.md - подробная архитектура
