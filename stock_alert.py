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
        f"<li><a href='{u}'>{t} [{s}]</a></li>"
        for t, u, s in items
    )

    resend.Emails.send({
        "from": "Alert <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": f"🔥 {shop}: {len(items)} produkter",
        "html": f"<h2>{shop}</h2><ul>{html}</ul>"
    })


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
    try:
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

    except:
        pass

    return "MISSING"


# ---------------- STOCK SIGNAL ----------------
def get_stock_signal(page):
    try:
        body = (page.inner_text("body") or "").lower()

        signals = []

        if "på lager" in body:
            signals.append("INSTOCK")

        if "ikke på lager" in body:
            signals.append("OUTOFSTOCK")

        if "ikke på nettlager" in body:
            signals.append("NO_WEBSTOCK")

        if "nettlager" in body:
            signals.append("WEBSTOCK")

        if "utsolgt" in body:
            signals.append("SOLDOUT")

        return "|".join(signals)

    except:
        return "UNKNOWN"


# ---------------- HASH ----------------
def make_hash(title, button_state, stock_signal):
    raw = f"{title}-{button_state}-{stock_signal}"
    return hashlib.md5(raw.encode()).hexdigest()


def base_url_from(url):
    return url.split("/")[2]


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
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            # raskere enn 500ms
            page.wait_for_timeout(200)

            # hent side-status ÉN gang
            state = get_button_state(page)
            stock_signal = get_stock_signal(page)

            # scan kun ekte linker (stor speedup)
            links = page.query_selector_all("a[href]")

            for el in links:
                try:
                    text = (el.inner_text() or "").strip()

                    if not text:
                        continue

                    if not is_match(text):
                        continue

                    href = el.get_attribute("href")

                    if not href:
                        continue

                    full_url = href

                    if href.startswith("/"):
                        full_url = (
                            "https://"
                            + base_url_from(url)
                            + href
                        )

                    h = make_hash(
                        text,
                        state,
                        stock_signal
                    )

                    old = cache.get(full_url)

                    is_new = old is None
                    changed = (
                        old and
                        old.get("hash") != h
                    )

                    cache[full_url] = {
                        "title": text,
                        "button": state,
                        "stock": stock_signal,
                        "hash": h
                    }

                    if is_new or changed:
                        items.append((
                            text[:120],
                            full_url,
                            state
                        ))

                except:
                    continue

            # ---------------- PAGINATION ----------------
            next_btn = page.query_selector(
                "a[rel='next'], "
                "a:has-text('Neste'), "
                "a:has-text('Next')"
            )

            if next_btn:
                try:
                    next_url = next_btn.get_attribute("href")

                    if next_url:
                        if next_url.startswith("/"):
                            next_url = (
                                "https://"
                                + base_url_from(url)
                                + next_url
                            )

                        if next_url not in visited:
                            queue.append(next_url)

                except:
                    pass

        except Exception as e:
            print(f"Feil på {url}: {e}")
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
                items = scrape(page, url, cache)

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
