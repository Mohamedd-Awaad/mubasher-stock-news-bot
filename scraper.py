import json
import os
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


URL = "https://www.mubasher.info/news/eg/pulse/stocks"
BASE_URL = "https://www.mubasher.info"
STATE_FILE = Path("sent_news.json")

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MubasherStockNewsBot/1.0)",
    "Accept-Language": "ar,en;q=0.9",
}


def load_sent_links():
    if not STATE_FILE.exists():
        return set()

    try:
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()


def save_sent_links(sent_links):
    limited_links = list(sent_links)[-500:]

    STATE_FILE.write_text(
        json.dumps(limited_links, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=20,
    )

    response.raise_for_status()


def fetch_news():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    news_items = []

    for link in soup.find_all("a", href=True):
        title = " ".join(link.get_text(" ", strip=True).split())
        href = link["href"]

        if not title:
            continue

        full_url = urljoin(BASE_URL, href)

        if "/news/" not in full_url:
            continue

        if len(title) < 20:
            continue

        if title in [
            "أخبار الأسهم",
            "أخبار الشركة",
            "تقييمات وتوصيات الأسهم",
            "مصر",
            "الأسهم",
        ]:
            continue

        news_items.append(
            {
                "title": title,
                "url": full_url,
            }
        )

    unique_items = []
    seen_urls = set()

    for item in news_items:
        if item["url"] not in seen_urls:
            unique_items.append(item)
            seen_urls.add(item["url"])

    return unique_items[:20]


def main():
    sent_links = load_sent_links()
    latest_news = fetch_news()

    new_items = [
        item for item in latest_news
        if item["url"] not in sent_links
    ]

    for item in reversed(new_items):
        message = (
            "🟢 <b>New Mubasher Stock News</b>\n\n"
            f"<b>{item['title']}</b>\n\n"
            f"{item['url']}"
        )

        send_telegram_message(message)
        sent_links.add(item["url"])

    save_sent_links(sent_links)

    print(f"Checked {len(latest_news)} items. Sent {len(new_items)} new items.")


if __name__ == "__main__":
    main()
