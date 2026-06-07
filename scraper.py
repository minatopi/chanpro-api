from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime, timedelta

URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"
DATA_FILE = "data.json"


# -------------------------
# 安定パース
# -------------------------
def parse_card(text):
    try:
        lines = text.split("\n")
        title = lines[0].strip()

        like = 0
        views = 0

        for l in lines:
            l_lower = l.lower()

            if "like" in l_lower:
                like = int("".join(filter(str.isdigit, l)))
            if "view" in l_lower:
                views = int("".join(filter(str.isdigit, l)))

        return {
            "title": title,
            "like": like,
            "views": views
        }
    except:
        return None


# -------------------------
# キー正規化（超重要）
# -------------------------
def make_key(item):
    return item["title"].strip().replace(" ", "").replace("　", "")


# -------------------------
# スクレイプ（container固定）
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
# データ読み込み（壊れ対策）
# -------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"current": [], "changes": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "current" not in data:
            data["current"] = []
        if "changes" not in data:
            data["changes"] = []

        return data

    except:
        return {"current": [], "changes": []}


# -------------------------
# 差分計算（ここが本体）
# -------------------------
def make_diff(old_list, new_list):
    old_map = {make_key(x): x for x in old_list}

    changes = []

    for n in new_list:
        key = make_key(n)
        old = old_map.get(key)

        # 初回はスキップ（全部newになるバグ防止）
        if not old:
            continue

        if old["like"] != n["like"] or old["views"] != n["views"]:
            changes.append({
                "type": "update",
                "data": n,
                "time": datetime.now().isoformat()
            })

    return changes


# -------------------------
# old / delete 管理
# -------------------------
def cleanup_changes(changes):
    now = datetime.now()
    result = []

    for c in changes:
        t = datetime.fromisoformat(c["time"])

        # 7日以上削除
        if now - t > timedelta(days=7):
            continue

        # 1日以上 old化
        if now - t > timedelta(days=1):
            c["type"] = "old"

        result.append(c)

    return result


# -------------------------
# メイン処理
# -------------------------
def main():
    data = load_data()

    old_current = data["current"]
    new_current = scrape_posts()

    print("OLD:", len(old_current))
    print("NEW:", len(new_current))

    changes = make_diff(old_current, new_current)

    # current更新
    data["current"] = new_current

    # changes追加
    data["changes"].extend(changes)

    # 期限整理
    data["changes"] = cleanup_changes(data["changes"])

    # 保存
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("CHANGES:", len(changes))


if __name__ == "__main__":
    main()
