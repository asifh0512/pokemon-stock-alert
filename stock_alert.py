import os
import json
import hashlib
import resend
from playwright.sync_api import sync_playwright

resend.api_key = os.environ["RESEND_API_KEY"]

EMAIL_TO = "asifh0512@gmail.com"

CACHE_FILE = "product_cache.json"


# ---------------- SITES ----------------
SITES = {
    "Ringo": "https://www.ringo.no/produkt-kategori/hobby/samlekort-og-spillkort/",
    "Norli": "https://www.norli.no/leker/kreative-leker/samlekort/pokemonkort/",
    "Nille": "https://www.nille.no/produkter/barnerom-og-leker/spill/",
    "Extra Leker": "https://www.extra-leker.no/merker-leketoy/pokemon_tcg"
}


# ---------------- CACHE ----------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


# ---------------- MATCHING ----------------
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


# ---------------- BUTTON STATE ----------------
def get_button_state(page):
    buttons = page.query_selector_all("button, a, input")

    for b in buttons:
        try:
            text = (b.inner_text() or "").lower()

            disabled = b.get_attribute("disabled")
            aria_disabled = b.get_attribute("aria-disabled")

            if any(x in text for x in [
                "handlekurv",
                "kjøp",
                "buy",
                "add to cart"
            ]):
                if disabled or aria_disabled == "true":
                    return "DISABLED"
                return "ACTIVE"

        except:
            continue

    return "MISSING"


# ---------------- STOCK ----------------
def get_stock_signal(page):
    try:
        body = (page.inner_text("body") or "").lower()

        signals = []

        if "på lager" in body:
            signals.append("INSTOCK")

        if "ikke på lager" in body:
            signals.append("OUTOFSTOCK")

        if "nettlager" in body:
            signals.append("WEBSTOCK")

        if "utsolgt" in body:
            signals.append("SOLDOUT")

        return "|".join(signals) if signals else "UNKNOWN"

    except:
        return "UNKNOWN"


# ---------------- HASH ----------------
def make_hash(title, button_state, stock_signal):
    return hashlib.md5(
        f"{title}-{button_state}-{stock_signal}".encode()
    ).hexdigest()


def base_url_from(url):
    return url.split("/")[2]


# ---------------- EMAIL ----------------
def send_email(shop, items):
    if not items:
        print(f"{shop}: ingen treff → ingen mail")
        return

    html = "".join(
        f"<li><a href='{u}'>{t} [{s}]</a></li>"
        for t, u, s in items
    )

    resend.Emails.send({
        "from": "Alert <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": f"🔥 {shop}: {len(items)} produkter",
        "html": f"<h2>{shop}</h2><ul>{html}</ul>"
    })

    print(f"{shop}: mail sendt ({len(items)})")


# ---------------- SCRAPER ----------------
def scrape(page, entry_url, cache):
    items = []
    visited = set()
    queue = [entry_url]

    while queue:
        url = queue.pop(0)

        if url in visited:
            continue

        visited.add(url)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(300)

            state = get_button_state(page)
            stock_signal = get_stock_signal(page)

            elements = page.query_selector_all(
                "a[href], div, article, li, span"
            )

            for el in elements:
                try:
                    text = " ".join((el.inner_text() or "").split()).strip()
                    href = el.get_attribute("href")

                    if not text or not href:
                        continue

                    full_url = href

                    if href.startswith("/"):
                        full_url = "https://" + base_url_from(url) + href

                    if not is_match(text):
                        continue

                    key = full_url
                    h = make_hash(text, state, stock_signal)

                    cache[key] = {
                        "title": text,
                        "button": state,
                        "stock": stock_signal,
                        "hash": h
                    }

                    items.append((text[:120], full_url, state))

                except:
                    continue

        except:
            continue

    return items


# ---------------- MAIN (ONE SHOT FOR GITHUB) ----------------
def main():
    cache = load_cache()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for shop, url in SITES.items():
            print(f"\nSjekker {shop}")

            try:
                raw_items = scrape(page, url, cache)

                clean_items = [
                    (t, u, s)
                    for t, u, s in raw_items
                    if t and u and len(t.strip()) > 2
                ]

                print(f"{shop}: funnet {len(clean_items)} produkter")

                if clean_items:
                    send_email(shop, clean_items)
                else:
                    print(f"{shop}: ingen treff")

            except Exception as e:
                print(f"Feil {shop}: {e}")

        browser.close()

    save_cache(cache)


if __name__ == "__main__":
    main()
