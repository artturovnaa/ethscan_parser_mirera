# ethscan_parser_mirera

**Что делает**
- Дёргает `https://etherscan.io/tokens` (или указанный `--source`) и парсит токены.
- Извлекает: *название/тикер*, *цену в USD (float)*, *ссылку на страницу токена*.
- Сортирует по убыванию цены.
- Сохраняет результат в **JSON** (`--out`).

## Запуск

```bash
# 1) Установите зависимости
pip install -r requirements.txt

# 2) Базовый запуск
python parse_crypto.py --limit 30 --out tokens.json

# 3) Явно указать URL
python parse_crypto.py --source https://etherscan.io/tokens --limit 50 --out out.json

# 4) Локальный HTML-файл (если скачивали ранее)
python parse_crypto.py --source ./tokens.html --limit 100 --out result.json
```

## Формат JSON
```json
[
  {"token": "Wrapped BTC (WBTC)", "price_usd": 86333.0, "url": "https://etherscan.io/token/0x..."},
  ...
]
```

## Примечания
- Скрипт использует `requests` и `beautifulsoup4` + `lxml`.
- Если структура страницы изменится, может понадобиться обновление селекторов.

Задачи:
1. Извлечь для каждой позиции: название токена (или тикер), цену в USD (как число), ссылку на страницу токена (по возможности).
2. Отсортировать список по убыванию цены (самые дорогие сверху).
3. Позволить пользователю задать количество позиций для вывода.