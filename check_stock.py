"""
Surveille la disponibilité d'un produit sur PlayStation Direct et envoie
une notification push (ntfy) quand il revient en stock.

Le HTML brut de la page contient tous les états possibles en même temps
("Actuellement Indisponible", "Ajouter au panier"...). Le vrai statut est
choisi par le JavaScript de la page : on utilise donc un vrai navigateur
(Playwright/Chromium) et on regarde ce qui est réellement VISIBLE.
"""

import json
import os
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = os.environ.get(
    "PRODUCT_URL",
    "https://direct.playstation.com/fr-fr/buy-accessories/lego-astro-bot",
)
PRODUCT_NAME = os.environ.get("PRODUCT_NAME", "LEGO Astro Bot")
TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
STATE_FILE = pathlib.Path("state.json")
SCREENSHOT = pathlib.Path("last_check.png")

# Libellés surveillés (comparaison insensible à la casse)
LABELS = {
    "add_to_cart": "ajouter au panier",
    "login_to_buy": "connectez-vous pour acheter",
    "preorder": "précommander",
    "unavailable": "actuellement indisponible",
    "coming_soon": "prochaine sortie",
}

DETECT_JS = """
(labels) => {
  const visible = (el) => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden'
        && parseFloat(s.opacity || '1') > 0 && r.width > 0 && r.height > 0;
  };
  const disabled = (el) => {
    const b = el.closest('button, [aria-disabled]');
    return !!b && (b.disabled === true || b.getAttribute('aria-disabled') === 'true');
  };
  const all = [...document.querySelectorAll('body *')];
  const out = {};
  for (const [key, text] of Object.entries(labels)) {
    const hits = all.filter(e => (e.textContent || '').trim().toLowerCase() === text);
    out[key] = hits.some(e => visible(e) && !disabled(e));
  }
  return out;
}
"""


def notify(title: str, message: str, priority: int = 4, tags=None) -> None:
    if not TOPIC:
        print("NTFY_TOPIC manquant : notification non envoyée.")
        return
    payload = {
        "topic": TOPIC,
        "title": title,
        "message": message,
        "priority": priority,
        "tags": tags or [],
        "click": URL,
    }
    req = urllib.request.Request(
        "https://ntfy.sh/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        print(f"Notification envoyée ({resp.status}) : {title}")


def read_status() -> tuple[str, dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="fr-FR",
            timezone_id="Europe/Paris",
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        try:
            page.wait_for_load_state("networkidle", timeout=30_000)
        except PWTimeout:
            pass
        page.wait_for_timeout(5_000)  # laisse le temps à l'appel de stock

        title = page.title() or ""
        head = (page.inner_text("body") or "")[:800].lower()
        seen = page.evaluate(DETECT_JS, LABELS)
        page.screenshot(path=str(SCREENSHOT), full_page=False)
        browser.close()

    print(f"Titre : {title!r}")
    print(f"Libellés visibles : {seen}")

    if "access denied" in title.lower() or "access denied" in head:
        return "blocked", seen
    if seen["unavailable"]:
        return "out_of_stock", seen
    if seen["add_to_cart"] or seen["login_to_buy"] or seen["preorder"]:
        return "in_stock", seen
    if seen["coming_soon"]:
        return "coming_soon", seen
    return "unknown", seen


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text("utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def main() -> int:
    if os.environ.get("TEST_NOTIFICATION", "").lower() == "true":
        notify(
            f"Test – alerte {PRODUCT_NAME}",
            "Si tu lis ceci, les notifications fonctionnent.",
            priority=3,
            tags=["white_check_mark"],
        )

    previous = load_state().get("status")
    try:
        status, seen = read_status()
    except Exception as exc:  # erreur réseau, timeout...
        print(f"Erreur pendant la vérification : {exc}")
        status, seen = "error", {}

    print(f"Statut précédent : {previous} → statut actuel : {status}")

    if status != previous:
        if status == "in_stock":
            notify(
                f"🎉 {PRODUCT_NAME} est de retour en stock !",
                "Le bouton d'achat est visible sur PlayStation Direct. Touche pour ouvrir la page.",
                priority=5,
                tags=["tada", "shopping_cart"],
            )
        elif status in ("blocked", "unknown", "error") and previous not in ("blocked", "unknown", "error"):
            notify(
                f"⚠️ Surveillance {PRODUCT_NAME} : statut illisible",
                f"Statut « {status} ». Le site bloque peut-être le robot : vérifie à la main en attendant.",
                priority=2,
                tags=["warning"],
            )
        elif status == "out_of_stock" and previous == "in_stock":
            notify(
                f"{PRODUCT_NAME} de nouveau indisponible",
                "Il est repassé en rupture.",
                priority=3,
                tags=["x"],
            )

    STATE_FILE.write_text(
        json.dumps(
            {
                "status": status,
                "seen": seen,
                "changed_at": datetime.now(timezone.utc).isoformat()
                if status != previous
                else load_state().get("changed_at"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        "utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
