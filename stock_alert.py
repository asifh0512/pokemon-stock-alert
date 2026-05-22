import os
import json
import hashlib
import resend
from playwright.sync_api import sync_playwright

resend.api_key = os.environ["RESEND_API_KEY"]
EMAIL_TO = "asifh0512@gmail.com"

CACHE_FILE = "product_cache.json"

MAX_PAGES = 25  # ⚡ speed limit


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


# ---------------- MATCH ----------------
def is_match(text):
    t = (text or "").lower()
    return any(k in t for k in [
        "mega evo",
        "prismatic",
        "destined rivals",
        "ascended",
        "pikachu",
        "chaos rising"
    ])


# ---------------- BUTTON ----------------
def get_button_state(page):
    for b in page.query_selector_all("button, a"):
        try:
            text = (b.inner_text() or "").lower()

            if any(x in text for x in ["handlekurv", "kjøp", "buy", "add to cart"]):
                if b.get_attribute("disabled") or b.get_attribute("aria-disabled") == "true":
                    return "DISABLED"
                return "ACTIVE"
        except:
            continue

    return "MISSING"


# ---------------- HASH ----------------
def make_hash(title, state):
    return hashlib.md5(f"{title}-{state}".encode()).hexdigest()


# ---------------- EMAIL ----------------
def send_email(shop, items):
    if not items:
        return

    html = "".join(
        f"<li><a href='{u}'>{t} [{s}]</a></li>" for t, u, s in items
    )

    resend.Emails.send({
        "from": "Alert <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": f"🔥 {shop}: {len(items)} produkter",
        "html": f"<h2>{shop}</h2><ul>{html}</ul>"
    })


# ---------------- SCRAPER ----------------
def scrape(page, entry_url, cache):
    queue = [entry_url]
    visited = set()
    items = []

    pages = 0

    while queue and pages < MAX_PAGES:
        url = queue.pop(0)

        if url in visited:
            continue
        visited.add(url)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            pages += 1

            # ---------------- ENTRY / LIST PAGE ----------------
            if "kategori" in url or "page=" in url:
                links = page.query_selector_all("a[href]")

                for a in links[:20]:  # ⚡ limit expansion
                    href = a.get_attribute("href")
                    if not href:
                        continue

                    if href.startswith("/"):
                        href = entry_url + href

                    if href not in visited:
                        queue.append(href)

                continue

            # ---------------- PRODUCT PAGE ----------------
            title = page.title()
            if not is_match(title):
                continue

            state = get_button_state(page)
            url_hash = make_hash(title, state)

            old = cache.get(url)

            is_new = old is None
            changed = old and old.get("hash") != url_hash
            state_changed = old and old.get("button") != state

            already_active = old and old.get("button") == "ACTIVE" and state == "ACTIVE"

            should_alert = (is_new or changed or state_changed) and not already_active

            cache[url] = {
                "title": title,
                "button": state,
                "hash": url_hash
            }

            if should_alert:
                items.append((title, url, state))

        except:
            continue

    return items


# ---------------- MAIN ----------------
def main():
    cache = load_cache()
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for shop, url in SITES.items():
            print(f"Sjekker {shop}")

            items = scrape(page, url, cache)

            seen = set()
            unique = []

            for t, u, s in items:
                if u not in seen:
                    seen.add(u)
                    unique.append((t, u, s))

            if unique:
                results[shop] = unique

        browser.close()

    save_cache(cache)

    for shop, items in results.items():
        send_email(shop, items)


if __name__ == "__main__":
    main()
