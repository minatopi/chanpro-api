from playwright.sync_api import sync_playwright
import json
import re
from datetime import datetime, timedelta

URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"
DATA_FILE = "data.json"


# -------------------------
# parse
# -------------------------
def parse_card(text: str):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

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


# -------------------------
# scrape
# -------------------------
def scrape_posts():

    results = []

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)

        container = page.locator(
            "div.bubble-element.Group.baTcwaH1"
        ).first

        container.wait_for()

        cards = container.locator(
            "div.clickable-element"
        ).all()

        for card in cards:
            try:
                item = parse_card(card.inner_text())
                if item:
                    results.append(item)
            except:
                pass

        browser.close()

    return results


# -------------------------
# load/save
# -------------------------
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "current": [],
            "changes": []
        }


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -------------------------
# main logic
# -------------------------
def main():

    new_posts = scrape_posts()
    old_data = load_data()

    old_posts = old_data.get("current", [])
    old_changes = old_data.get("changes", [])

    now = datetime.now()

    def key(p):
        return f"{p['title']}:{p['like']}:{p['views']}"

    old_map = {key(p): p for p in old_posts}
    new_map = {key(p): p for p in new_posts}

    changes = []

    # -------------------------
    # 差分検出
    # -------------------------
    for k, v in new_map.items():
        if k not in old_map:
            changes.append({
                "time": now.isoformat(),
                "type": "new",
                "data": v
            })

    for k, v in old_map.items():
        if k not in new_map:
            changes.append({
                "time": now.isoformat(),
                "type": "removed",
                "data": v
            })

    # -------------------------
    # 既存changesを寿命管理
    # -------------------------
    filtered_changes = []

    for c in old_changes:

        t = datetime.fromisoformat(c["time"])
        age = now - t

        # 7日以上 → 削除
        if age > timedelta(days=7):
            continue

        # それ以外 → 残す
        filtered_changes.append(c)

    # -------------------------
    # 1日経過したものは old扱いフラグ追加
    # -------------------------
    for c in filtered_changes:
        t = datetime.fromisoformat(c["time"])
        if now - t > timedelta(days=1):
            c["type"] = "old"

    # -------------------------
    # 新しいchanges追加
    # -------------------------
    filtered_changes.extend(changes)

    result = {
        "current": new_posts,
        "changes": filtered_changes
    }

    save_data(result)

    print("current:", len(new_posts))
    print("changes:", len(filtered_changes))


if __name__ == "__main__":
    main()
