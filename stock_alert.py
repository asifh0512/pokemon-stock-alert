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


# ---------------- SHARED NORLI-STYLE SCRAPER ----------------
def scrape_site(page, start_url):
    items = []
    visited = set()
    queue = [start_url]

    while queue:
        url = queue.pop(0)

        if url in visited:
            continue
        visited.add(url)

        try:
            page.goto(url, timeout=60000)
            page.wait_for_timeout(2000)

            # 1. scan elements (samme som Norli-logikk)
            for el in page.query_selector_all("a, div, article, li"):
                try:
                    text = (el.inner_text() or "").strip()
                    href = el.get_attribute("href")

                    if not text:
                        continue

                    if is_match(text):
                        full_url = href or url

                        if href and href.startswith("/"):
                            base = "https://" + start_url.split("/")[2]
                            full_url = base + href

                        items.append((text[:120], full_url))

                except:
                    continue

            # 2. pagination detection (samme for alle)
            next_btn = page.query_selector(
                "a[rel='next'], a:has-text('Neste'), a:has-text('Next')"
            )

            if next_btn:
                try:
                    next_url = next_btn.get_attribute("href")

                    if next_url:
                        if next_url.startswith("/"):
                            base = "https://" + start_url.split("/")[2]
                            next_url = base + next_url

                        if next_url not in visited:
                            queue.append(next_url)

                except:
                    pass

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
                items = scrape_site(page, url)

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
