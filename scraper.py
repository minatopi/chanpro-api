from playwright.sync_api import sync_playwright
import json
import re

URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"


def parse_card(text: str):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # ノイズ除去
    skip = ["ログイン", "Lv."]
    lines = [l for l in lines if not any(s in l for s in skip)]
    lines = [l for l in lines if l != "みなと"]

    if not lines:
        return None

    title = lines[0]

    nums = re.findall(r"\d+", text)

    return {
        "title": title,
        "like": int(nums[0]) if len(nums) > 0 else 0,
        "views": int(nums[1]) if len(nums) > 1 else 0
    }


def scrape_posts():

    results = []

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="domcontentloaded")

        # 安定化（重要）
        page.wait_for_timeout(8000)

        # ✅ 対象エリアに限定
        container = page.locator(
            "div.bubble-element.Group.baTcwaH1"
        ).first

        container.wait_for()

        # ✅ その中だけ取得
        cards = container.locator(
            "div.clickable-element"
        ).all()

        print("cards:", len(cards))

        for card in cards:

            try:
                text = card.inner_text()

                parsed = parse_card(text)

                if parsed:
                    results.append(parsed)

            except Exception as e:
                print("error:", e)

        browser.close()

    return results

if __name__ == "__main__":

    posts = scrape_posts()

    data = {
        "count": len(posts),
        "posts": posts
    }

    print("SCRAPED COUNT:", len(posts))

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )
