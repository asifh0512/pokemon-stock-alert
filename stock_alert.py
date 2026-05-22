import os
import resend
from playwright.sync_api import sync_playwright

resend.api_key = os.environ["RESEND_API_KEY"]

EMAIL_TO = "asifh0512@gmail.com"

SITES = {
    "Ringo": "https://www.ringo.no/pokemon/",
    "Norli": "https://www.norli.no/search?query=pokemon",
    "Nille": "https://www.nille.no/search?q=pokemon",
    "Extra Leker": "https://www.extra-leker.no/search?q=pokemon"
}


# ---------------- EMAIL (1 per butikk) ----------------
def send_email(shop, items):
    count = len(items)

    if count == 0:
        return

    html_items = ""
    for title, url in items:
        html_items += f"<li><a href='{url}'>{title}</a></li>"

    resend.Emails.send({
        "from": "Pokemon Alert <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": f"🔥 {shop}: {count} Pokémon produkter funnet",
        "html": f"""
        <h2>{shop}</h2>
        <p><b>{count} produkter funnet</b></p>
        <ul>
            {html_items}
        </ul>
        """
    })


# ---------------- SIMPLE FILTER (MIDlERTIDIG) ----------------
def is_pokemon(text):
    t = (text or "").lower()
    return "pokemon" in t or "pokémon" in t


# ---------------- STEP 1: FIND PRODUCTS ----------------
def extract_products(page, base_url):
    results = []

    for a in page.query_selector_all("a[href]"):
        try:
            text = (a.inner_text() or "").strip()
            href = a.get_attribute("href")

            if not text or not href:
                continue

            if href.startswith("/"):
                href = base_url + href

            if is_pokemon(text):
                results.append((text[:100], href))

        except:
            continue

    return results


# ---------------- MAIN ----------------
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for shop, url in SITES.items():
            print(f"\nSjekker {shop}")

            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(3000)

                products = extract_products(page, url)

                # fjern duplikater
                seen = set()
                unique = []

                for title, link in products:
                    if link not in seen:
                        seen.add(link)
                        unique.append((title, link))

                print(f"{shop}: fant {len(unique)} produkter")

                send_email(shop, unique)

            except Exception as e:
                print(f"Feil {shop}: {e}")

        browser.close()


if __name__ == "__main__":
    main()
