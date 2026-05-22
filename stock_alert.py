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


# ---------------- EMAIL ----------------
def send_email(shop, title, url):
    resend.Emails.send({
        "from": "Pokemon Alert <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": f"🔥 Produkt funnet hos {shop}",
        "html": f"""
        <h2>{shop}</h2>
        <p><b>{title}</b></p>
        <a href="{url}">Åpne produkt</a>
        """
    })


# ---------------- FILTER (uten exclude) ----------------
def is_pokemon_related(text: str):
    t = (text or "").lower()

    include_keywords = [
        "pokemonkort",
        "pokémonkort",
        "pokemon kort",
        "pokémon kort",
        "pokemon-kort",
        "pokémon-kort",
        "booster",
        "elite trainer",
        "tcg"
    ]

    return any(x in t for x in include_keywords)


# ---------------- LINK EXTRACTION ----------------
def extract_links(page, base_url):
    results = []

    # hent hele “cards”, ikke bare a-tags
    cards = page.query_selector_all("a, div, article")

    for c in cards:
        try:
            text = (c.inner_text() or "").strip().lower()
            href = c.get_attribute("href")

            if not text:
                continue

            if is_pokemon_related(text):
                if href:
                    if href.startswith("/"):
                        href = base_url + href
                    results.append((text[:80], href))
                else:
                    results.append((text[:80], page.url))

        except:
            continue

    return results

# ---------------- STOCK CHECK ----------------
def check_stock(page):
    html = page.content().lower()

    if "utsolgt" in html:
        return False
    if "ikke på lager" in html:
        return False
    if "ikke tilgjengelig" in html:
        return False

    if "på lager" in html:
        return True
    if "legg i handlekurv" in html:
        return True
    if "add to cart" in html:
        return True

    return None


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

                links = extract_links(page, url)
                print(f"{shop}: fant {len(links)} kandidater")

                for title, href in links[:10]:
                    try:
                        page.goto(href, timeout=60000)
                        page.wait_for_timeout(2000)

                        if check_stock(page):
                            print("ALERT:", title)
                            send_email(shop, title or "Produkt", href)

                    except:
                        continue

            except Exception as e:
                print(f"Feil på {shop}: {e}")

        browser.close()


if __name__ == "__main__":
    main()
