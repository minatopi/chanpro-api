from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime, timedelta

URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"

DATA_FILE = "data.json"


# -------------------------
# パース（あなたの既存関数想定）
# -------------------------
def parse_card(text):
    try:
        lines = text.split("\n")
        title = lines[0].strip()

        like = 0
        views = 0

        for l in lines:
            if "like" in l.lower():
                like = int("".join(filter(str.isdigit, l)))
            if "view" in l.lower():
                views = int("".join(filter(str.isdigit, l)))

        return {
            "title": title,
            "like": like,
            "views": views
        }
    except:
        return None


# -------------------------
# スクレイプ（重要：コンテナ限定）
# -------------------------
def scrape_posts():
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(5000)

        container = page.locator("div.bubble-element.Group.baTcwaH1")

        cards = container.locator("div.clickable-element").all()

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


# -------------------------
# データ読み込み
# -------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "current": [],
        "changes": []
    }


# -------------------------
# 差分計算（ここが修正ポイント）
# -------------------------
def make_diff(old_list, new_list):
    old_map = {
        (x["title"]): x for x in old_list
    }

    changes = []

    for n in new_list:
        title = n["title"]
        old = old_map.get(title)

        # 初回は new にしない（全部入るバグ防止）
        if not old:
            continue

        # like / views が変わったものだけ
        if old["like"] != n["like"] or old["views"] != n["views"]:
            changes.append({
                "type": "update",
                "data": n,
                "time": datetime.now().isoformat()
            })

    return changes


# -------------------------
# 期限管理
# -------------------------
def cleanup_changes(changes):
    now = datetime.now()
    result = []

    for c in changes:
        t = datetime.fromisoformat(c["time"])

        # 1週間以上削除
        if now - t > timedelta(days=7):
            continue

        # 1日以上 → oldにする
        if now - t > timedelta(days=1):
            c["type"] = "old"

        result.append(c)

    return result


# -------------------------
# メイン
# -------------------------
def main():
    old_data = load_data()
    old_current = old_data["current"]

    new_current = scrape_posts()

    changes = make_diff(old_current, new_current)

    # current更新
    old_data["current"] = new_current

    # changes追加
    old_data["changes"].extend(changes)

    # 期限処理
    old_data["changes"] = cleanup_changes(old_data["changes"])

    # 保存
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(old_data, f, ensure_ascii=False, indent=2)

    print("SCRAPED:", len(new_current))
    print("CHANGES:", len(changes))


if __name__ == "__main__":
    main()
