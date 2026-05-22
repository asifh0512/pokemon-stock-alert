import os
import requests
from bs4 import BeautifulSoup
import resend

resend.api_key = os.environ["RESEND_API_KEY"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

SEARCH_URLS = {
    "Ringo": "https://www.ringo.no/pokemon/",
    "Norli": "https://www.norli.no/search?query=pokemon",
    "Nille": "https://www.nille.no/search?q=pokemon",
    "Extra Leker": "https://www.extra-leker.no/search?q=pokemon"
}

# 1. Finn produktlenker fra søkesider
def get_product_links(shop, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        links = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]

            # filtrer typiske produktlenker
            if "produkt" in href or "/p/" in href:
                if href.startswith("/"):
                    if shop == "Norli":
                        href = "https://www.norli.no" + href
                    elif shop == "Ringo":
                        href = "https://www.ringo.no" + href

                links.add(href)

        return list(links)

    except Exception as e:
        print(f"Feil på {shop} søk: {e}")
        return []

# 2. Sjekk ekte produkt-side
def check_product(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        html = r.text.lower()

        # ekte signaler
        if "utsolgt" in html:
            return False
        if "ikke på lager" in html:
            return False
        if "legg i handlekurv" in html:
            return True
        if "på lager" in html:
            return True

        return None

    except:
        return None

# 3. Send e-post
def send_email(shop, url):
    resend.Emails.send({
        "from": "Pokemon Alert <onboarding@resend.dev>",
        "to": ["asifh0512@gmail.com"],
        "subject": f"🔥 Pokémon på lager hos {shop}",
        "html": f"<h3>{shop} har noe på lager!</h3><a href='{url}'>Åpne produkt</a>"
    })

def main():
    send_email("TEST", "https://example.com")
    for shop, search_url in SEARCH_URLS.items():

        print(f"Sjekker {shop}...")

        product_links = get_product_links(shop, search_url)

        for product_url in product_links[:10]:  # begrensning for speed
            status = check_product(product_url)

            if status is True:
                send_email(shop, product_url)
                print("ALERT:", product_url)

main()
