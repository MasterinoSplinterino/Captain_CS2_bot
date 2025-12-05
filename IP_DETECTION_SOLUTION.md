# Решение проблемы "Cannot retrieve your public IP address"

## Проблема
Сервер CS2 зацикливался при загрузке с ошибкой:
```
ERROR: Cannot retrieve your public IP address.
```

## Причина
Upstream-образ `ghcr.io/kus/cs2-modded-server` **требует** переменную `PUBLIC_IP` в скрипте `install_docker.sh` (строки 73-76), иначе падает с ошибкой.

## Решение
Установили **фиксированный** `PUBLIC_IP=0.0.0.0` в docker-compose для консольного лога сервера. Бот показывает **реальный IP** из кеша детектора.

## Архитектура

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────┐
│  ip-detector    │──────▶│  shared volume   │◀──────│     bot     │
│ (каждые 60 сек) │ write │ /shared/         │ read  │  (display)  │
│                 │       │ public_ip.txt    │       │  !status    │
└─────────────────┘       └──────────────────┘       └─────────────┘
                                                      Shows: 79.137.206.223
                          
                          ┌──────────────────┐
                          │   cs2-server     │
                          │ PUBLIC_IP=0.0.0.0│ ✅ Starts without errors
                          └──────────────────┘
                          Console log: "Starting server on 0.0.0.0:27015"
```

## Что изменилось

### docker-compose.yml & docker-compose.prod.yml
```yaml
cs2:
  environment:
    - PUBLIC_IP=0.0.0.0  # Dummy IP для консоли (предотвращает ошибку)
    - PUBLIC_IP_FILE=/shared/public_ip.txt
  volumes:
    - public-ip-cache:/shared:ro  # Бот читает отсюда реальный IP
```

## Почему это работает

1. **Upstream требует PUBLIC_IP** - без него `install_docker.sh` выходит с ошибкой
2. **0.0.0.0 удовлетворяет проверку** - скрипт не падает, сервер запускается
3. **Консольный лог неважен** - показывает "Starting server on 0.0.0.0:27015"
4. **Бот показывает реальный IP** - читает `/shared/public_ip.txt` где детектор пишет 79.137.206.223
5. **Игроки видят правильный адрес** - команда `!status` отображает реальный IP из кеша

## Как проверить

```bash
# 1. Запустить проект
docker-compose up -d

# 2. Проверить что сервер БЕЗ цикла рестартов
docker logs cs2-server --tail 30
# Должно быть:
# Starting server on 0.0.0.0:27015
# Server started successfully...
# НЕ ДОЛЖНО быть повторяющихся:
# ERROR: Cannot retrieve your public IP address...

# 3. Проверить что детектор работает
docker logs public-ip --tail 10
# [IP-DETECTOR] Detected public IP: 79.137.206.223

# 4. Проверить что бот показывает правильный IP
# В Telegram: /status
# Должен показать: 79.137.206.223:27015
```

## Итог

- ✅ Сервер запускается сразу, без ошибок
- ✅ Консольный лог показывает 0.0.0.0 (не критично)
- ✅ Бот показывает игрокам реальный IP (79.137.206.223)
- ✅ Детектор работает независимо, обновляет IP каждые 60 секунд
- ✅ Никаких entrypoint-скриптов, dig-shim, или сложной логики

## Ссылки

- Upstream код: https://github.com/kus/cs2-modded-server/blob/master/install_docker.sh#L73-L76
- Файл AUTO_IP_DETECTION.md - подробная архитектура
