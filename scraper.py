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
