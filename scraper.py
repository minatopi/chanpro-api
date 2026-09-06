import json
import re
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


# ============================================================
# 設定
# ============================================================

PROFILE_URL = (
    "https://chanpro.jp/"
    "00-program-profile/"
    "1724731678594x659718187856833700"
)

OUTPUT_FILE = "data.json"

WAIT_MS = 8000


# ============================================================
# 共通
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# 数字解析
# ============================================================

def parse_number(text):
    """
    文字列から数字を取得する。

    例:
        "1,234" -> 1234
        "1234"  -> 1234
        ""      -> None
    """

    if text is None:
        return None

    text = str(text).replace(",", "").strip()

    if not re.fullmatch(r"\d+", text):
        return None

    try:
        return int(text)
    except ValueError:
        return None


# ============================================================
# カード解析
# ============================================================

def parse_card(card):
    """
    プロフィールページ内の1作品カードを解析する。

    重要:
    カード全体に対して \d+ を実行しない。

    例えば、

        タイトル123
        Lv.10
        100
        500

    のようなカードの場合、

        タイトル123 → タイトル
        Lv.10      → 除外
        100        → いいね
        500        → 閲覧数

    として処理する。

    また、いいねが0の場合に表示されないケース:

        タイトル
        Lv.10
        500

    なら、

        likes = 0
        views = 500

    とする。
    """

    try:
        text = card.inner_text()

    except Exception as e:
        print("カードのinner_text取得失敗:", e)
        return None

    print()
    print("--------------------------------------------------")
    print("CARD TEXT")
    print("--------------------------------------------------")
    print(text)
    print("--------------------------------------------------")

    # --------------------------------------------------------
    # 行分割
    # --------------------------------------------------------

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return None

    # --------------------------------------------------------
    # 不要な行を除外
    # --------------------------------------------------------

    cleaned_lines = []

    for line in lines:

        # ログイン
        if line == "ログイン":
            continue

        # Lv.10 / Lv.5 など
        if re.fullmatch(r"Lv\.\s*\d+", line):
            continue

        # 元コードで不要だった文字
        if line == "みなと":
            continue

        cleaned_lines.append(line)

    if not cleaned_lines:
        return None

    # --------------------------------------------------------
    # タイトル
    # --------------------------------------------------------

    title = cleaned_lines[0]

    # --------------------------------------------------------
    # 数字だけの行を取得
    # --------------------------------------------------------

    numbers = []

    for line in cleaned_lines[1:]:

        number = parse_number(line)

        if number is not None:
            numbers.append(number)

    # --------------------------------------------------------
    # いいね / 閲覧数
    # --------------------------------------------------------

    if len(numbers) >= 2:

        likes = numbers[0]
        views = numbers[1]

    elif len(numbers) == 1:

        # いいねが0の場合、いいね側の数字が表示されない
        likes = 0
        views = numbers[0]

    else:

        likes = 0
        views = 0

    return {
        "title": title,
        "likes": likes,
        "views": views
    }


# ============================================================
# カードURL
# ============================================================

def get_card_url(card):
    """
    カード内のaタグから作品URLを取得する。

    URLが見つからない場合はNone。
    """

    try:

        links = card.locator("a")

        count = links.count()

        for i in range(count):

            try:

                href = links.nth(i).get_attribute("href")

                if not href:
                    continue

                href = href.strip()

                # 相対URL
                if href.startswith("/"):
                    href = "https://chanpro.jp" + href

                if href.startswith("https://"):
                    return href

                if href.startswith("http://"):
                    return href

            except Exception:
                continue

    except Exception as e:

        print("URL取得エラー:", e)

    return None


# ============================================================
# プロフィール取得
# ============================================================

def scrape_profile(profile_url):
    """
    ChanProプロフィールページから作品一覧を取得する。
    """

    results = []

    with sync_playwright() as p:

        print()
        print("=" * 70)
        print("Playwright起動")
        print("=" * 70)

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 2000
            },
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0.0.0 "
                "Safari/537.36"
            )
        )

        # ----------------------------------------------------
        # ページアクセス
        # ----------------------------------------------------

        print()
        print("プロフィールページ:")
        print(profile_url)

        page.goto(
            profile_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print()
        print(
            f"{WAIT_MS / 1000:.1f}秒待機..."
        )

        page.wait_for_timeout(WAIT_MS)

        # ----------------------------------------------------
        # 作品一覧コンテナ
        # ----------------------------------------------------

        print()
        print("作品一覧コンテナを検索...")

        container = page.locator(
            "div.bubble-element.Group.baTcwaH1"
        ).first

        container.wait_for(
            state="visible",
            timeout=30000
        )

        print("作品一覧コンテナ取得成功")

        # ----------------------------------------------------
        # 作品カード
        # ----------------------------------------------------

        cards = container.locator(
            "div.clickable-element"
        )

        card_count = cards.count()

        print()
        print("=" * 70)
        print(
            f"作品カード数: {card_count}"
        )
        print("=" * 70)

        # ----------------------------------------------------
        # 各カード処理
        # ----------------------------------------------------

        for index in range(card_count):

            print()
            print()
            print("#" * 70)
            print(
                f"CARD {index + 1} / {card_count}"
            )
            print("#" * 70)

            try:

                card = cards.nth(index)

                # ------------------------------------------------
                # カード解析
                # ------------------------------------------------

                parsed = parse_card(card)

                if not parsed:

                    print(
                        "解析できなかったためスキップ"
                    )

                    continue

                # ------------------------------------------------
                # URL取得
                # ------------------------------------------------

                url = get_card_url(card)

                parsed["url"] = url

                # ------------------------------------------------
                # 識別キー
                #
                # URLが取れればURL。
                # URLがなければタイトル。
                # ------------------------------------------------

                if url:
                    parsed["key"] = url
                else:
                    parsed["key"] = parsed["title"]

                # ------------------------------------------------
                # 結果追加
                # ------------------------------------------------

                results.append(parsed)

                print()
                print("取得結果")
                print(
                    f"タイトル : {parsed['title']}"
                )
                print(
                    f"いいね   : {parsed['likes']}"
                )
                print(
                    f"閲覧数   : {parsed['views']}"
                )
                print(
                    f"URL      : {parsed['url']}"
                )
                print(
                    f"KEY      : {parsed['key']}"
                )

            except Exception as e:

                print()
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print(
                    f"CARD {index + 1} 処理失敗"
                )
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print(e)

        browser.close()

    return results


# ============================================================
# JSON保存
# ============================================================

def save_json(posts):
    """
    取得結果をdata.jsonに保存する。
    """

    data = {
        "last_updated": now_iso(),
        "count": len(posts),
        "posts": posts
    }

    # 一時ファイルに保存してから置換
    # 途中で停止してJSONが壊れるのを防ぐ。
    temp_file = OUTPUT_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    import os

    os.replace(
        temp_file,
        OUTPUT_FILE
    )

    return data


# ============================================================
# メイン
# ============================================================

def main():

    started_at = now_iso()

    print()
    print("=" * 70)
    print("ChanPro プロフィール作品スクレイピング")
    print("=" * 70)

    print()
    print(
        f"開始時刻: {started_at}"
    )

    print()
    print(
        f"URL: {PROFILE_URL}"
    )

    # --------------------------------------------------------
    # スクレイピング
    # --------------------------------------------------------

    posts = scrape_profile(
        PROFILE_URL
    )

    # --------------------------------------------------------
    # JSON保存
    # --------------------------------------------------------

    data = save_json(
        posts
    )

    # --------------------------------------------------------
    # 結果
    # --------------------------------------------------------

    print()
    print()
    print("=" * 70)
    print("スクレイピング完了")
    print("=" * 70)

    print(
        f"SCRAPED COUNT : {data['count']}"
    )

    print(
        f"UPDATED       : {data['last_updated']}"
    )

    print()
    print("取得作品:")

    for index, post in enumerate(
        posts,
        start=1
    ):

        print(
            f"{index}. "
            f"{post['title']} "
            f"/ いいね={post['likes']} "
            f"/ 閲覧={post['views']}"
        )

    print()
    print(
        f"{OUTPUT_FILE} 保存完了"
    )

    print("=" * 70)


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()
