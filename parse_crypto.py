import json
import os
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = "https://etherscan.io/tokens"

PRICE_RE = re.compile(r"\$?\s?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)")


def extract_price(text: str):
    m = PRICE_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except:
        return None


def parse_tokens(html: str, base_url: str):
    soup = BeautifulSoup(html, "lxml")

    rows = soup.select("tr")
    items = []
    seen = set()

    for row in rows:
        text = row.get_text(" ", strip=True)
        price = extract_price(text)
        if price is None:
            continue

        a = row.find("a", href=True)
        if not a:
            continue

        name = a.get_text(" ", strip=True)
        href = a["href"]
        url = urljoin(base_url, href)

        key = (name, url)
        if key in seen:
            continue
        seen.add(key)

        items.append({
            "token": name,
            "price_usd": price,
            "url": url
        })

    items.sort(key=lambda x: x["price_usd"], reverse=True)
    return items


def fetch_html(source):
    if not source:
        source = DEFAULT_URL

    # Если это URL
    p = urlparse(source)
    if p.scheme in ("http", "https"):
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        r = requests.get(source, headers=headers, timeout=20)
        r.raise_for_status()
        return r.text

    # Если локальный файл
    if os.path.isfile(source):
        with open(source, "r", encoding="utf-8") as f:
            return f.read()

    raise ValueError("Неверный источник: укажите URL или путь к HTML файлу.")


def run_parser(source=None, limit=50, output="tokens.json"):
    html = fetch_html(source)
    data = parse_tokens(html, DEFAULT_URL)

    if limit > 0:
        data = data[:limit]

    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Сохранено {len(data)} записей в {output}")
    for r in data[:3]:
        print(f"- {r['token']} | ${r['price_usd']} | {r['url']}")


if __name__ == "__main__":
    import sys

    source = None
    limit = 50
    output = "tokens.json"

    args = sys.argv[1:]
    try:
        if "--source" in args:
            source = args[args.index("--source") + 1]
        if "--limit" in args:
            limit = int(args[args.index("--limit") + 1])
        if "--out" in args:
            output = args[args.index("--out") + 1]
    except:
        print("Игнорируем ошибочные аргументы.")

    run_parser(source, limit, output)
