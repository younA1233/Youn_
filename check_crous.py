#!/usr/bin/env python3
"""
CROUS Watcher (multi-villes) — surveille plusieurs zones sur
trouverunlogement.lescrous.fr et poste un message Telegram dès qu'un
nouveau logement apparaît, en précisant la ville.

Variables d'environnement requises :
  TELEGRAM_BOT_TOKEN   Token du bot (donné par @BotFather)
  TELEGRAM_CHAT_ID     ID du canal/chat où poster (ex. -1001234567890)
  CITIES_JSON          Liste JSON des villes à surveiller, ex :
    [
      {"name": "Grenoble", "url": "https://trouverunlogement.lescrous.fr/tools/XX/search?bounds=..."},
      {"name": "Paris",    "url": "https://trouverunlogement.lescrous.fr/tools/XX/search?bounds=..."}
    ]

Variable optionnelle :
  MAX_RUNTIME_MIN    Durée max d'exécution en minutes (défaut 55)
"""

import os
import re
import sys
import json
import time
import requests
from bs4 import BeautifulSoup

STATE_FILE = "seen.json"
POLL_INTERVAL_SEC = 30
DEFAULT_MAX_RUNTIME_MIN = 55

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def load_seen():
    """Structure : {"NomVille": ["id1", "id2", ...], ...}"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {city: set(ids) for city, ids in data.items()}
    return {}


def save_seen(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({city: sorted(ids) for city, ids in seen.items()}, f, ensure_ascii=False, indent=2)


def fetch_listings(search_url):
    resp = requests.get(search_url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    listings = []
    cards = soup.select("[class*='fr-card']")
    for card in cards:
        text = card.get_text(" ", strip=True)
        if not text or "€" not in text or "m²" not in text:
            continue

        link_tag = card.find("a", href=True)
        href = link_tag["href"] if link_tag else None
        if href and href.startswith("/"):
            href = "https://trouverunlogement.lescrous.fr" + href

        listing_id = href or text
        title_match = re.search(r"^[^\d€]+", text)
        title = title_match.group(0).strip() if title_match else text[:60]

        listings.append({
            "id": listing_id,
            "title": title,
            "text": text,
            "url": href or search_url,
        })
    return listings


def telegram_send(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        if not r.ok:
            print(f"[!] Erreur Telegram : {r.status_code} {r.text}", file=sys.stderr)
    except requests.RequestException as e:
        print(f"[!] Échec envoi Telegram : {e}", file=sys.stderr)


def notify_listing(token, chat_id, city, listing):
    text = (
        f"🏠 <b>Nouveau logement à {city}</b>\n"
        f"{listing['title'][:100]}\n"
        f"{listing['url']}"
    )
    telegram_send(token, chat_id, text)


def notify_summary(token, chat_id, city, count):
    telegram_send(
        token, chat_id,
        f"🏠 <b>{count} nouveaux logements à {city}</b> d'un coup — va voir le site directement, ça va vite.",
    )


def notify_startup(token, chat_id, cities):
    names = ", ".join(c["name"] for c in cities)
    telegram_send(token, chat_id, f"✅ Surveillance active pour : {names}")


def check_city(token, chat_id, city_name, search_url, seen_for_city, first_run):
    try:
        listings = fetch_listings(search_url)
    except requests.RequestException as e:
        print(f"[!] Erreur de récupération pour {city_name} : {e}", file=sys.stderr)
        return seen_for_city

    current_ids = {l["id"] for l in listings}
    new_ids = current_ids - seen_for_city

    if new_ids and not first_run:
        new_listings = [l for l in listings if l["id"] in new_ids]
        print(f"[+] {city_name} : {len(new_listings)} nouveau(x) logement(s)")
        if len(new_listings) > 8:
            notify_summary(token, chat_id, city_name, len(new_listings))
        else:
            for listing in new_listings:
                notify_listing(token, chat_id, city_name, listing)
    elif first_run:
        print(f"[i] {city_name} : premier passage, {len(current_ids)} logement(s) enregistré(s) silencieusement")

    return seen_for_city | current_ids


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    cities_json = os.environ.get("CITIES_JSON")
    max_runtime_min = float(os.environ.get("MAX_RUNTIME_MIN", DEFAULT_MAX_RUNTIME_MIN))

    if not token or not chat_id or not cities_json:
        print("[!] TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID et CITIES_JSON doivent être définis.", file=sys.stderr)
        sys.exit(1)

    try:
        cities = json.loads(cities_json)
    except json.JSONDecodeError as e:
        print(f"[!] CITIES_JSON invalide : {e}", file=sys.stderr)
        sys.exit(1)

    seen = load_seen()
    first_run = len(seen) == 0
    if first_run:
        notify_startup(token, chat_id, cities)

    for city in cities:
        seen.setdefault(city["name"], set())

    deadline = time.time() + max_runtime_min * 60
    iteration = 0

    while time.time() < deadline:
        for city in cities:
            seen[city["name"]] = check_city(
                token, chat_id, city["name"], city["url"],
                seen[city["name"]], first_run and iteration == 0,
            )
        save_seen(seen)
        iteration += 1
        time.sleep(POLL_INTERVAL_SEC)

    print("[i] Fin de session (relais pris par le prochain déclenchement planifié).")


if __name__ == "__main__":
    main()
