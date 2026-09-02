from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime, timezone
import json
import re
import time


# ============================================================
# 設定
# ============================================================

URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"

OUTPUT_FILE = "data.json"

# ページ読み込み後の待機時間（ミリ秒）
WAIT_AFTER_LOAD = 8000

# カードを取得するセレクタ
CARD_SELECTOR = "div.clickable-element"

# カードを入れる親コンテナ
CONTAINER_SELECTOR = "div.bubble-element.Group.baTcwaH1"


# ============================================================
# ユーティリティ
# ============================================================

def clean_text(text):
    """
    余計な空白・改行を削除
    """
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def extract_like(text):
    """
    「19こ」「100こ」などから数字を取得
    """
    if not text:
        return 0

    match = re.search(r"(\d+)\s*こ", text)

    if match:
        return int(match.group(1))

    return 0


def extract_progress(text):
    """
    「275/1000」などから現在値を取得

    戻り値:
        current, total

    例:
        275/1000
        -> (275, 1000)
    """

    if not text:
        return 0, 0

    match = re.search(r"(\d+)\s*/\s*(\d+)", text)

    if match:
        current = int(match.group(1))
        total = int(match.group(2))

        return current, total

    return 0, 0


# ============================================================
# カード解析
# ============================================================

def parse_card(card):
    """
    1つのカードから

        title
        like
        views

    を取得する。
    """

    try:

        # ----------------------------------------------------
        # カード内のText要素を取得
        # ----------------------------------------------------

        text_elements = card.locator(
            "div.bubble-element.Text"
        ).all_inner_texts()

        # 空文字削除・整形
        texts = []

        for text in text_elements:

            text = clean_text(text)

            if text:
                texts.append(text)

        if not texts:
            return None


        # ----------------------------------------------------
        # カード全体のテキスト
        # ----------------------------------------------------

        full_text = "\n".join(texts)


        # ----------------------------------------------------
        # 名前
        # ----------------------------------------------------
        #
        # 今回の構造では最初のTextが名前。
        #
        # 「みなと」などの固定値には依存しない。
        #

        title = texts[0]


        # ----------------------------------------------------
        # いいね数
        # ----------------------------------------------------

        like = 0

        for text in texts:

            value = extract_like(text)

            if value:
                like = value
                break


        # ----------------------------------------------------
        # 進捗
        # ----------------------------------------------------

        views = 0
        total = 0

        for text in texts:

            current, max_value = extract_progress(text)

            if current or max_value:

                views = current
                total = max_value

                break


        # ----------------------------------------------------
        # 結果
        # ----------------------------------------------------

        return {
            "title": title,
            "like": like,
            "views": views,
            "total": total
        }


    except Exception as e:

        print("カード解析エラー:", e)

        return None


# ============================================================
# スクレイピング
# ============================================================

def scrape_posts():

    results = []


    with sync_playwright() as p:

        print("ブラウザ起動中...")

        browser = p.chromium.launch(
            headless=True
        )


        page = browser.new_page()


        # ----------------------------------------------------
        # ページアクセス
        # ----------------------------------------------------

        print("ページを開いています...")

        try:

            page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

        except PlaywrightTimeoutError:

            print("ページ読み込みがタイムアウトしました。")


        # ----------------------------------------------------
        # Bubbleの描画待ち
        # ----------------------------------------------------

        print(
            f"{WAIT_AFTER_LOAD / 1000:.1f}秒待機中..."
        )

        page.wait_for_timeout(
            WAIT_AFTER_LOAD
        )


        # ----------------------------------------------------
        # コンテナ取得
        # ----------------------------------------------------

        print("カードコンテナを探しています...")

        try:

            container = page.locator(
                CONTAINER_SELECTOR
            ).first

            container.wait_for(
                state="visible",
                timeout=30000
            )

        except PlaywrightTimeoutError:

            print(
                "カードコンテナが見つかりませんでした。"
            )

            browser.close()

            return results


        # ----------------------------------------------------
        # カード取得
        # ----------------------------------------------------

        cards = container.locator(
            CARD_SELECTOR
        )

        card_count = cards.count()

        print(
            f"カード数: {card_count}"
        )


        # ----------------------------------------------------
        # 各カードを解析
        # ----------------------------------------------------

        for i in range(card_count):

            try:

                card = cards.nth(i)

                parsed = parse_card(card)


                if parsed:

                    results.append(
                        parsed
                    )

                    print(
                        f"[{i + 1}/{card_count}] "
                        f"{parsed['title']} "
                        f"like={parsed['like']} "
                        f"views={parsed['views']}/"
                        f"{parsed['total']}"
                    )

                else:

                    print(
                        f"[{i + 1}/{card_count}] "
                        "解析できませんでした"
                    )


            except Exception as e:

                print(
                    f"[{i + 1}/{card_count}] "
                    f"エラー: {e}"
                )


        # ----------------------------------------------------
        # ブラウザ終了
        # ----------------------------------------------------

        browser.close()


    return results


# ============================================================
# JSON保存
# ============================================================

def save_json(posts):

    data = {

        "last_updated":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "count":
            len(posts),

        "posts":
            posts
    }


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


    return data


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("スクレイピング開始")
    print("=" * 60)


    start_time = time.time()


    # --------------------------------------------------------
    # スクレイピング
    # --------------------------------------------------------

    posts = scrape_posts()


    # --------------------------------------------------------
    # JSON保存
    # --------------------------------------------------------

    data = save_json(
        posts
    )


    elapsed = time.time() - start_time


    # --------------------------------------------------------
    # 結果表示
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("スクレイピング完了")
    print("=" * 60)

    print(
        f"取得件数: {data['count']}"
    )

    print(
        f"更新日時: {data['last_updated']}"
    )

    print(
        f"処理時間: {elapsed:.2f}秒"
    )

    print(
        f"保存先: {OUTPUT_FILE}"
    )

    print("=" * 60)
