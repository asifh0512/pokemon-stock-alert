import os
import resend
from playwright.sync_api import sync_playwright

resend.api_key = os.environ["RESEND_API_KEY"]
EMAIL_TO = "asifh0512@gmail.com"


# ---------------- SITES ----------------
SITES = {
    "Ringo": "https://www.ringo.no/produkt-kategori/hobby/samlekort-og-spillkort/",
    "Norli": "https://www.norli.no/leker/kreative-leker/samlekort/pokemonkort/",
    "Nille": "https://www.nille.no/produkter/barnerom-og-leker/spill/",
    "Extra Leker": "https://www.extra-leker.no/merker-leketoy/pokemon_tcg"
}


# ---------------- MATCH ----------------
def is_match(text):
    t = (text or "").lower()

    keywords = [
        "mega evo",
        "prismatic",
        "destined rivals",
        "ascended",
        "chaos rising",

        # bred test
        "pokemon"
    ]

    return any(k in t for k in keywords)


# ---------------- EMAIL ----------------
def send_email(shop, items):
    if not items:
        print(f"[{shop}] Ingen treff → ingen mail")
        return

    html = "".join(
        f"<li><a href='{u}'>{t}</a></li>"
        for t, u in items
    )

    resend.Emails.send({
        "from": "Alert <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": f"🔥 {shop}: {len(items)} produkter funnet",
        "html": f"""
        <h2>{shop}</h2>
        <p>Fant {len(items)} produkter:</p>
        <ul>{html}</ul>
        """
    })

    print(f"[{shop}] Mail sendt ({len(items)} treff)")


# ---------------- SCRAPER ----------------
def scrape(page, entry_url):
    queue = [entry_url]
    visited = set()
    items = []

    while queue:
        url = queue.pop(0)

        if url in visited:
            continue

        visited.add(url)

        try:
            print("Besøker:", url)

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            # --------- Finn nye linker ---------
            links = page.query_selector_all("a[href]")

            for a in links[:20]:
                href = a.get_attribute("href")

                if not href:
                    continue

                if href.startswith("/"):
                    base = (
                        url.split("/")[0]
                        + "//"
                        + url.split("/")[2]
                    )
                    href = base + href

                if href not in visited:
                    queue.append(href)

            # --------- Match produkt ---------
            title = page.title()

            print("TITLE:", title)

            if is_match(title):
                print("MATCH:", title)

                items.append((title, url))

        except Exception as e:
            print("FEIL:", url, e)

    # Fjern duplicates
    seen = set()
    unique = []

    for t, u in items:
        if u not in seen:
            seen.add(u)
            unique.append((t, u))

    return unique


# ---------------- MAIN ----------------
def main():
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        for shop, url in SITES.items():
            print(f"\n==== {shop} ====")

            items = scrape(page, url)

            if items:
                results[shop] = items

        browser.close()

    for shop, items in results.items():
        send_email(shop, items)


if __name__ == "__main__":
    main()
