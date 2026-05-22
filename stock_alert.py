import os
import resend
from playwright.sync_api import sync_playwright

# API KEY (fra GitHub Secrets)
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
        "subject": f"🔥 Pokémon funnet hos {shop}",
        "html": f"""
        <h2>{shop}</h2>
        <p><b>{title}</b></p>
        <a href="{url}">Åpne produkt</a>
        """
    })


# ---------------- FILTER ----------------
def is_pokemon(text: str):
    t = (text or "").lower()
    keywords = ["pokemon", "pokémon", "booster", "tcg", "elite trainer", "charizard", "pikachu"]
    return any(k in t for k in keywords)


# ---------------- LINK EXTRACTION ----------------
def extract_links(page):
    results = []

    for a in page.query_selector_all("a"):
        try:
            text = a.inner_text() or ""
            href = a.get_attribute("href")

            if not href:
                continue

            if is_pokemon(text):
                results.append((text.strip(), href))

        except:
            continue

    return results


# ---------------- STOCK CHECK ----------------
def check_stock(page):
    html = page.content().lower()

    if "utsolgt" in html:
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


# ---------------- URL FIX ----------------
def fix_url(base, href):
    if href.startswith("http"):
        return href

    if "ringo.no" in base:
        return "https://www.ringo.no" + href

    if "norli.no" in base:
        return "https://www.norli.no" + href

    if "nille.no" in base:
        return "https://www.nille.no" + href

    if "extra-leker.no" in base:
        return "https://www.extra-leker.no" + href

    return href


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

                links = extract_links(page)
                print(f"{shop}: fant {len(links)} kandidater")

                for title, href in links[:10]:
                    full_url = fix_url(url, href)

                    try:
                        page.goto(full_url, timeout=60000)
                        page.wait_for_timeout(2000)

                        if check_stock(page):
                            print("ALERT:", title)
                            send_email(shop, title or "Pokémon produkt", full_url)

                    except:
                        continue

            except Exception as e:
                print(f"Feil på {shop}: {e}")

        browser.close()


if __name__ == "__main__":
    main()
