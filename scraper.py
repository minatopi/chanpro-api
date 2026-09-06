from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
import json
import re

URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"


def parse_card(text: str):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 不要な文字だけ除外
    lines = [
        l for l in lines
        if l not in ["ログイン"]
        and not l.startswith("Lv.")
    ]

    if not lines:
        return None

    # 最初の文字列をタイトルとして扱う
    title = lines[0]

    # 数字を取得
    nums = re.findall(r"\d+", text)

    return {
        "title": title,
        "like": int(nums[0]) if len(nums) >= 1 else 0,
        "views": int(nums[1]) if len(nums) >= 2 else 0
    }


def scrape_posts():

    results = []

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        print("ページを開いています...")

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(8000)

        # プロフィール内のカードを探す
        container = page.locator(
            "div.bubble-element.Group.baTcwaH1"
        ).first

        container.wait_for()

        cards = container.locator(
            "div.clickable-element"
        ).all()

        print("cards:", len(cards))

        for i, card in enumerate(cards):

            try:

                text = card.inner_text()

                print(f"\n--- CARD {i + 1} ---")
                print(text)

                parsed = parse_card(text)

                if parsed:
                    results.append(parsed)

            except Exception as e:

                print(
                    f"CARD {i + 1} error:",
                    e
                )

        browser.close()

    return results


if __name__ == "__main__":

    posts = scrape_posts()

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "count": len(posts),
        "posts": posts
    }

    print("\n====================")
    print("SCRAPED COUNT:", len(posts))
    print("UPDATED:", data["last_updated"])
    print("====================")

    with open(
        "data.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("data.json を保存しました")
