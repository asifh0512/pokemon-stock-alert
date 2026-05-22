def check_product(page):
    title = page.title() or ""

    try:
        desc = page.locator("meta[name='description']").get_attribute("content") or ""
    except:
        desc = ""

    html = page.content().lower()
    combined = f"{title} {desc} {html}"

    # ---------------------------
    # ❌ HARD FALSE (overstyr alt)
    # ---------------------------
    if "utsolgt" in combined:
        return None
    if "ikke på lager" in combined:
        return None
    if "ikke på nettlager" in combined:
        return None
    if "ikke tilgjengelig" in combined:
        return None

    # ---------------------------
    # 🟢 POSITIVE SIGNALS
    # ---------------------------
    if any(x in combined for x in [
        "på lager",
        "legg i handlekurv",
        "add to cart",
        "kjøp nå"
    ]):
        return title.strip() or "Pokémon produkt"

    return None
