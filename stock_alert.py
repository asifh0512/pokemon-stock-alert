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
def send_email(shop, items):
    count = len(items)

    if count == 0:
        return

    html_items = ""
    for title, url in items:
        html_items += f"<li><a href='{url}'>{title}</a></li>"

    resend.Emails.send({
        "from": "Alert <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": f"🔥 {shop}: {count} produkter funnet",
        "html": f"""
        <h2>{shop}</h2>
        <p><b>{count} produkter funnet</b></p>
        <ul>{html_items}</ul>
        """
    })


# ---------------- FILTER (SERIER) ----------------
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


# ---------------- SCRAPER ----------------
def extract_products(page, base_url):
    results = []

    elements = page.query_selector_all("a, div, article, li")

    for el in elements:
        try:
            text = (el.inner_text() or "").strip()
            href = el.get_attribute("href")

            if not text:
                continue

            text_l = text.lower()

            if is_match(text_l):
                if href:
                    if href.startswith("/"):
                        href = base_url + href

                results.append((text[:120], href or page.url))

        except:
            continue

    return results


# ---------------- MAIN ----------------
def main():
    with sync
