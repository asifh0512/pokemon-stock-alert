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


# ---------------- MATCH ----------------
def is_match(text):
    t = (text or "").lower()
    return any(k in t for k in [
        "mega evo",
        "prismatic",
        "destined rivals",
        "ascended",
        "chaos rising"
    ])


# ---------------- ENTRY VS PRODUCT DETECTION ----------------
def is_entry_page(page):
    try:
        links = page.query_selector_all("a[href]")
        text = page.inner_text("body") or ""

        link_count = len(links)

        # Heuristics:
        has_many_links = link_count > 25
        has_no_clear_product_title = len(text.split("\n")) > 200

        return has_many_links and has_no_clear_product_title

    except:
        return True


# ---------------- PRODUCT LINKS ----------------
def extract_links(page, base_url):
    urls = []

    for a in page.query_selector_all("a[href]"):
        href = a.get_attribute("href")
        if not href:
            continue

        if href.startswith("/"):
            href = base_url + href

        urls.append(href)

    return urls[:20]


# ---------------- HASH ----------------
def make_hash(title):
    return hashlib.md5(title.encode()).hexdigest()


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


# ---------------- SCRAPER ----------------
def scrape(page, entry_url, cache):
    queue = [entry_url]
    visited = set()
    items = []

    while queue:
        url = queue.pop(0)

        if url in visited:
            continue
        visited.add(url)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # ---------------- ENTRY PAGE ----------------
            if is_entry_page(page):
                links = extract_links(page, entry_url)

                for link in links:
                    if link not in visited:
                        queue.append(link)

                continue

            # ---------------- PRODUCT PAGE ----------------
            title = page.title()

            if not is_match(title):
                continue

            h = make_hash(title)

            old = cache.get(url)

            is_new = old is None
            changed = old and old.get("hash") != h

            cache[url] = {
                "title": title,
                "hash": h
            }

            if is_new or changed:
                items.append((title, url))

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

            for t, u in items:
                if u not in seen:
                    seen.add(u)
                    unique.append((t, u))

            if unique:
                results[shop] = unique

        browser.close()

    save_cache(cache)

    for shop, items in results.items():
        send_email(shop, items)


if __name__ == "__main__":
    main()
