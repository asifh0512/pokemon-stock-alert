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


# ---------------- KEYWORDS ----------------
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

            if any(x in text for x in ["handlekurv", "kjøp", "buy", "add to cart"]):
                if disabled or aria_disabled == "true":
                    return "DISABLED"
                return "ACTIVE"

        except:
            continue

    return "MISSING"


# ---------------- HASH ----------------
def make_hash(title, button_state):
    raw = f"{title}-{button_state}"
    return hashlib.md5(raw.encode()).hexdigest()


# ---------------- URL COLLECTOR ----------------
def extract_urls(page, base_url):
    urls = set()

    for a in page.query_selector_all("a[href]"):
        try:
            href = a.get_attribute("href")
            if not href:
                continue

            if href.startswith("/"):
                href = base_url + href

            if base_url.split("/")[2] in href:
                urls.add(href)

        except:
            continue

    return list(urls)


# ---------------- NORLI SCRAPER ----------------
def scrape_norli(page, url, cache):
    items = []
    visited = set()
    queue = [url]

    while queue:
        current = queue.pop(0)

        if current in visited:
            continue
        visited.add(current)

        page.goto(current, timeout=60000)
        page.wait_for_timeout(2000)

        for el in page.query_selector_all("a, div, article, li"):
            try:
                text = (el.inner_text() or "").strip()
                href = el.get_attribute("href")

                if not text:
                    continue

                if is_match(text):
                    full_url = href or current

                    if href and href.startswith("/"):
                        full_url = "https://www.norli.no" + href

                    state = get_button_state(page)
                    h = make_hash(text, state)

                    old = cache.get(full_url)
                    is_new = old is None
                    changed = old and old.get("hash") != h

                    cache[full_url] = {
                        "title": text,
                        "button": state,
                        "hash": h
                    }

                    if is_new or changed or state == "ACTIVE":
                        items.append((text[:120], full_url, state))

            except:
                continue

        next_btn = page.query_selector("a[rel='next'], a:has-text('Neste'), a:has-text('Next')")

        if next_btn:
            try:
                next_url = next_btn.get_attribute("href")

                if next_url and next_url not in visited:
                    if next_url.startswith("/"):
                        next_url = "https://www.norli.no" + next_url
                    queue.append(next_url)

            except:
                pass

    return items


# ---------------- GENERIC SCRAPER ----------------
def scrape_generic(page, entry_url, cache):
    items = []

    page.goto(entry_url, timeout=60000)
    page.wait_for_timeout(3000)

    urls = extract_urls(page, entry_url)

    for u in urls[:25]:
        try:
            page.goto(u, timeout=60000)
            page.wait_for_timeout(1500)

            title = page.title()
            state = get_button_state(page)

            if not is_match(title):
                continue

            h = make_hash(title, state)

            old = cache.get(u)
            is_new = old is None
            changed = old and old.get("hash") != h

            cache[u] = {
                "title": title,
                "button": state,
                "hash": h
            }

            if is_new or changed or state == "ACTIVE":
                items.append((title, u, state))

        except:
            continue

    return items


# ---------------- MAIN ----------------
def main():
    cache = load_cache()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for shop, url in SITES.items():
            print(f"\nSjekker {shop}")

            try:
                if shop == "Norli":
                    items = scrape_norli(page, url, cache)
                else:
                    items = scrape_generic(page, url, cache)

                seen = set()
                unique = []

                for t, u, s in items:
                    if u not in seen:
                        seen.add(u)
                        unique.append((t, u, s))

                print(f"{shop}: {len(unique)} funnet")

                send_email(shop, unique)

            except Exception as e:
                print(f"Feil {shop}: {e}")

        browser.close()

    save_cache(cache)


if __name__ == "__main__":
    main()
