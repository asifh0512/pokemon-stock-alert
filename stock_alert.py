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

def get_product_links(url):
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "produkt" in href or "/p/" in href or "/products" in href:
            if href.startswith("/"):
                href = "https://www.norli.no" + href
            links.add(href)

    return list(links)

def is_in_stock(html):
    text = html.lower()

    # alt som tyder på tilgjengelighet
    if "utsolgt" in text:
        return False
    if "ikke tilgjengelig" in text:
        return False
    if "på lager" in text:
        return True
    if "legg i handlekurv" in text:
        return True
    if "add to cart" in text:
        return True

    return None

def check_product(url):
    r = requests.get(url, headers=HEADERS, timeout=10)
    return is_in_stock(r.text)

def send_email(shop, url):
    resend.Emails.send({
        "from": "Pokemon Alert <onboarding@resend.dev>",
        "to": ["asifh0512@gmail.com"],
        "subject": f"🔥 Pokémon mulig på lager hos {shop}",
        "html": f"<p>Mulig tilgjengelig Pokémon-produkt</p><a href='{url}'>Åpne produkt</a>"
    })

def main():
    for shop, url in SEARCH_URLS.items():
        print(f"Sjekker {shop}")

        products = get_product_links(url)

        for p in products[:8]:  # holder det lett og stabilt
            status = check_product(p)

            if status is True:
                send_email(shop, p)
                print("ALERT:", p)

main()
