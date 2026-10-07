"""Bot 2: scrape product listings (books.toscrape.com) -> Excel."""
import logging
import re
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
from excel_writer import append_rows

HEADERS = ["Scraped At", "Title", "Price", "Rating (1-5)", "In Stock", "Alert", "URL"]
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_page(html, page_url):
    """Return (rows, next_page_url or None). Pure function - easy to test."""
    soup = BeautifulSoup(html, "html.parser")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for item in soup.select("article.product_pod"):
        title = item.h3.a["title"]
        url = urljoin(page_url, item.h3.a["href"])
        price = float(re.sub(r"[^\d.]", "", item.select_one("p.price_color").text))
        stars = item.select_one("p.star-rating")["class"][1]
        in_stock = "In stock" in item.select_one("p.availability").text
        alert = "BELOW TARGET" if price < config.PRICE_ALERT else ""
        rows.append([stamp, title, price, RATINGS.get(stars, 0), in_stock, alert, url])
    nxt = soup.select_one("li.next a")
    return rows, (urljoin(page_url, nxt["href"]) if nxt else None)


def run():
    """Scrape up to MAX_PAGES pages. Returns (rows_saved, failed_pages)."""
    url, all_rows, failed = config.WEB_START_URL, [], 0
    for page_no in range(1, config.MAX_PAGES + 1):
        if not url:
            break
        try:
            resp = requests.get(url, timeout=15,
                                headers={"User-Agent": "RPA-Prototype/1.0 (learning project)"})
            resp.raise_for_status()
            resp.encoding = "utf-8"
            rows, url = parse_page(resp.text, resp.url)
            all_rows.extend(rows)
            logging.info("WEB OK        page %d -> %d items", page_no, len(rows))
            time.sleep(config.REQUEST_DELAY)
        except Exception as exc:
            logging.error("WEB FAIL      page %d: %s", page_no, exc)
            failed += 1
            break

    if all_rows:
        append_rows("Products", HEADERS, all_rows)
        alerts = sum(1 for r in all_rows if r[5])
        logging.info("WEB ALERTS    %d item(s) below %.2f", alerts, config.PRICE_ALERT)
    return len(all_rows), failed
