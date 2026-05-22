import os
import resend
from playwright.sync_api import sync_playwright

resend.api_key = os.environ["RESEND_API_KEY"]

EMAIL_TO = "asifh0512@gmail.com"

SITES = {
    "Ringo": "https://www.ringo.no",
    "Norli": "https://www.norli.no/leker/kreative-leker/samlekort/pokemonkort",
    "Nille": "https://www.nille.no",
    "Extra Leker": "https://www.extra-leker.no"
}


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


# ---------------- PRODUCT CHECK ----------------
def check_product(page):
    title = page.title() or ""
    html = page.content().lower()

    if "utsolgt" in html:
        return None
    if "ikke på lager" in html:
        return None
    if "ikke på nettlager" in html:
        return None

    if is_match(title):
        return title

    return None


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

                urls = extract_urls(page, url)
                print(f"{shop}: fant {len(urls)} URLs")

                items = []

                for u in urls[:25]:
                    try:
                        page.goto(u, timeout=60000)
                        page.wait_for_timeout(1500)

                        result = check_product(page)

                        if result:
                            items.append((result, u))

                    except:
                        continue

                # dedupe
                seen = set()
                unique = []

                for t, u in items:
                    if u not in seen:
                        seen.add(u)
                        unique.append((t, u))

                print(f"{shop}: {len(unique)} funnet")
                send_email(shop, unique)

            except Exception as e:
                print(f"Feil {shop}: {e}")

        browser.close()


if __name__ == "__main__":
    main()
