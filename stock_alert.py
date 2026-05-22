import os
import resend
from playwright.sync_api import sync_playwright

resend.api_key = os.environ["RESEND_API_KEY"]

EMAIL_TO = "asifh0512@gmail.com"

# ---------------- ENTRY POINTS ----------------
SITES = {
    "Ringo": "https://www.ringo.no/produkt-kategori/hobby/samlekort-og-spillkort/",
    "Norli": "https://www.norli.no/leker/kreative-leker/samlekort/pokemonkort/",
    "Nille": "https://www.nille.no/produkter/barnerom-og-leker/spill/",
    "Extra Leker": "https://www.extra-leker.no/merker-leketoy/pokemon_tcg"
}


# ---------------- EMAIL ----------------
def send_email(shop, items):
    if not items:
        return

    html = "".join(
        f"<li><a href='{u}'>{t}</a></li>" for t, u in items
    )

    resend.Emails.send({
        "from": "Alert <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": f"🔥 {shop}: {len(items)} produkter",
        "html": f"<h2>{shop}</h2><ul>{html}</ul>"
    })


# ---------------- KEYWORDS ----------------
def is_match(text):
    t = (text or "").lower()

    keywords = [
        "mega evo",
        "prismatic",
        "destined rivals",
        "ascended",
        "chaos rising"
    ]

    return any(k in t for k in keywords)


# ---------------- URL COLLECTION (NON-NORLI) ----------------
def extract_urls(page, base_url):
    urls = set()

    for a in page.query_selector_all("a[href]"):
        try:
            href = a.get_attribute("href")
            if not href:
                continue

            if href.startswith("/"):
                href = base_url + href

            if base_url.split("/")[2] in href:
                urls.add(href)

        except:
            continue

    return list(urls)


# ---------------- NORLI (TITLE-BASED) ----------------
def scrape_norli(page, url):
    items = []

    page.goto(url, timeout=60000)
    page.wait_for_timeout(3000)

    pages = set()
    queue = [url]

    while queue:
        current = queue.pop(0)

        if current in pages:
            continue
        pages.add(current)

        page.goto(current, timeout=60000)
        page.wait_for_timeout(2000)

        # hent alle product-like elements
        for el in page.query_selector_all("a, div, article, li"):
            try:
                text = (el.inner_text() or "").strip()
                href = el.get_attribute("href")

                if not text:
                    continue

                if is_match(text):
                    full_url = href or current
                    if href and href.startswith("/"):
                        full_url = "https://www.norli.no" + href

                    items.append((text[:120], full_url))

            except:
                continue

        # finn neste sider (pagination)
        next_btn = page.query_selector("a[rel='next'], a:has-text('Neste'), a:has-text('Next')")

        if next_btn:
            try:
                next_url = next_btn.get_attribute("href")
                if next_url and next_url.startswith("/"):
                    next_url = "https://www.norli.no" + next_url

                if next_url:
                    queue.append(next_url)
            except:
                pass

    return items


# ---------------- OTHER SHOPS (URL -> PRODUCT PAGES) ----------------
def scrape_by_urls(page, entry_url):
    items = []

    page.goto(entry_url, timeout=60000)
    page.wait_for_timeout(3000)

    urls = extract_urls(page, entry_url)

    for u in urls[:25]:
        try:
            page.goto(u, timeout=60000)
            page.wait_for_timeout(1500)

            title = page.title()

            if is_match(title):
                items.append((title, u))

        except:
            continue

    return items


# ---------------- MAIN ----------------
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for shop, url in SITES.items():
            print(f"\nSjekker {shop}")

            try:
                # ---------------- NORLI SPECIAL ----------------
                if shop == "Norli":
                    items = scrape_norli(page, url)
                else:
                    items = scrape_by_urls(page, url)

                # dedupe
                seen = set()
                unique = []

                for t, u in items:
                    if u not in seen:
                        seen.add(u)
                        unique.append((t, u))

                print(f"{shop}: {len(unique)} funnet")

                send_email(shop, unique)

            except Exception as e:
                print(f"Feil {shop}: {e}")

        browser.close()


if __name__ == "__main__":
    main()
