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


# ---------------- ENTRY PAGE FILTER (IMPORTANT) ----------------
def is_entry_or_list_page(url):
    if not url:
        return True

    url = url.lower()

    return any(x in url for x in [
        "produkt-kategori",
        "kategori",
        "page=",
        "/page/",
        "samlekort"  # entry listing pages (safe block)
    ])


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
def make_hash(title, state):
    return hashlib.md5(f"{title}-{state}".encode()).hexdigest()


# ---------------- EMAIL ----------------
def send_email(shop, items):
    if not items:
        return  # HARD STOP: ingen mail uten treff

    html = "".join(
        f"<li><a href='{u}'>{t} [{s}]</a></li>" for t, u, s in items
    )

    resend.Emails.send({
        "from": "Alert <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": f"🔥 {shop}: {len(items)} produkter",
        "html": f"<h2>{shop}</h2><ul>{html}</ul>"
    })


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

        # ❌ SKIP ENTRY / LIST PAGES
        if is_entry_or_list_page(url):
            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(1500)

                # only use for discovery, NOT cache
                urls = extract_urls(page, entry_url)
                queue.extend(urls[:10])

            except:
                continue

            continue

        try:
            page.goto(url, timeout=60000)
            page.wait_for_timeout(2000)

            title = page.title()
            state = get_button_state(page)

            if not is_match(title):
                continue

            h = make_hash(title, state)

            old = cache.get(url)
            is_new = old is None
            changed = old and old.get("hash") != h

            cache[url] = {
                "title": title,
                "state": state,
                "hash": h
            }

            if is_new or changed or state == "ACTIVE":
                items.append((title, url, state))

        except:
            continue

    return items


# ---------------- MAIN ----------------
def main():
    cache = load_cache()
    all_results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for shop, url in SITES.items():
            print(f"\nSjekker {shop}")

            try:
                items = scrape(page, url, cache)

                # dedupe
                seen = set()
                unique = []

                for t, u, s in items:
                    if u not in seen:
                        seen.add(u)
                        unique.append((t, u, s))

                print(f"{shop}: {len(unique)} funnet")

                # STORE RESULT BUT DO NOT AUTO SEND
                if unique:
                    all_results[shop] = unique

            except Exception as e:
                print(f"Feil {shop}: {e}")

        browser.close()

    save_cache(cache)

    # ---------------- SEND EMAIL ONLY IF ANY RESULTS ----------------
    for shop, items in all_results.items():
        send_email(shop, items)


if __name__ == "__main__":
    main()
