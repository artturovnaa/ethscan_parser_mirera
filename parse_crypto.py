import argparse
import json
import os
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = "https://etherscan.io/tokens"

PRICE_RE = re.compile(r"\$?\s?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)")


def extract_price(text: str) -> Optional[float]:
    for m in PRICE_RE.finditer(text):
        start = m.start()
        dollar_before = text[max(0, start - 2):start]
        if "$" in dollar_before or text[start:start + 1] == "$":
            try:
                return float(m.group(1).replace(",", ""))
            except:
                continue
    return None


def ensure_base(url_or_html_source: str, soup: BeautifulSoup) -> str:
    try:
        p = urlparse(url_or_html_source)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    except Exception:
        pass
    base_tag = soup.find("base")
    if base_tag and base_tag.get("href"):
        try:
            p = urlparse(base_tag["href"])
            if p.scheme and p.netloc:
                return f"{p.scheme}://{p.netloc}"
        except Exception:
            pass
    canon = soup.find("link", rel=lambda v: v and "canonical" in v)
    if canon and canon.get("href"):
        try:
            p = urlparse(canon["href"])
            if p.scheme and p.netloc:
                return f"{p.scheme}://{p.netloc}"
        except Exception:
            pass
    return "https://etherscan.io"


def parse_tokens(html: str, source_hint: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    base = ensure_base(source_hint, soup)

    anchors = soup.select('a[href*="/token/"], a[href*="/tokens/"], a[href*="/tokenholdings"]')

    results = []
    seen = set()

    def include(token: str, price: Optional[float], href: str):
        if price is None:
            return
        url_abs = urljoin(base + "/", href) if href else None
        key = (token, url_abs)
        if key in seen:
            return
        seen.add(key)
        results.append({"token": token, "price_usd": float(price), "url": url_abs})

    for a in anchors:
        href = a.get("href", "").strip()
        text = (a.get_text(" ", strip=True) or "").strip()
        if not href or not text:
            continue

        row = a.find_parent("tr")
        if row is None:
            row = a.find_parent(lambda tag: tag and tag.name in ["tr", "div", "li"] and (
                        tag.get("role") == "row" or tag.name in ["tr", "li", "div"]))
        row_text = row.get_text(" ", strip=True) if row else text
        price = extract_price(row_text)

        symbol = None
        for attr in ["data-symbol", "data-coin-symbol", "data-symbol-short"]:
            val = (row.get(attr) if row else None) or a.get(attr)
            if val:
                symbol = val.strip()
                break
        token_label = symbol or text
        include(token_label, price, href)

    if not results:
        for row in soup.select("tr"):
            row_text = row.get_text(" ", strip=True)
            price = extract_price(row_text)
            if price is None:
                continue
            a = row.find("a", href=True)
            if not a:
                continue
            token_label = a.get_text(" ", strip=True) or "UNKNOWN"
            include(token_label, price, a["href"])

    results.sort(key=lambda x: x["price_usd"], reverse=True)
    return results


def fetch_source(source: Optional[str]) -> str:
    if not source:
        url = DEFAULT_URL
    else:
        url = source

    # URL?
    try:
        p = urlparse(url)
        if p.scheme in ("http", "https"):
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            }
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            return r.text
    except Exception:
        pass

    if os.path.isfile(url):
        with open(url, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    raise SystemExit(f"Не удалось получить источник: {url}\n"
                     f"Укажите корректный URL или путь к локальному .html файлу.")


def main():
    ap = argparse.ArgumentParser(description="Парсер Etherscan Tokens -> JSON")
    ap.add_argument("--source", "-s", default=None,
                    help="URL или путь к локальному .html (по умолчанию: https://etherscan.io/tokens)")
    ap.add_argument("--limit", "-n", type=int, default=1000, help="Сколько записей вывести (по умолчанию 100)")
    ap.add_argument("--out", "-o", default="tokens.json", help="Путь к JSON-файлу результата")
    args = ap.parse_args()

    html = fetch_source(args.source)
    rows = parse_tokens(html, args.source or DEFAULT_URL)

    if args.limit and args.limit > 0:
        rows = rows[:args.limit]

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"Сохранено {len(rows)} записей в {args.out}")
    if rows:
        print("Топ-3 примера:")
        for r in rows[:3]:
            print(f"- {r['token']} | ${r['price_usd']} | {r['url']}")


if __name__ == "__main__":
    main()
