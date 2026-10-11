"""
Fetches today's Pokemon card prices and saves them.

  python fetch_prices.py          -> real run (needs internet)
  python fetch_prices.py --demo   -> writes fake sample data so you can preview the dashboard

What it writes:
  data/history.csv  one row per item per day (the permanent record)
  data/data.js      the same data in a form index.html can read
"""
import csv
import json
import os
import random
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib import error, parse, request

ROOT = Path(__file__).parent
WATCHLIST = ROOT / "watchlist.json"
HISTORY = ROOT / "data" / "history.csv"
DATA_JS = ROOT / "data" / "data.js"
ERAS = ROOT / "eras.json"
SETS_CACHE = ROOT / "data" / "sets.json"

API = "https://api.pokemontcg.io/v2"
FIELDS = ["date", "type", "id", "label", "price"]

# Which TCGplayer price type to use first (cards have different ones)
VARIANT_ORDER = [
    "holofoil", "1stEditionHolofoil", "unlimitedHolofoil",
    "normal", "1stEditionNormal", "reverseHolofoil",
]


def api_get(path, params=None):
    url = API + path
    if params:
        url += "?" + parse.urlencode(params)
    headers = {"User-Agent": "pokemon-dashboard"}
    key = os.environ.get("POKEMONTCG_API_KEY")
    if key:
        headers["X-Api-Key"] = key
    for attempt in range(1, 4):
        try:
            with request.urlopen(request.Request(url, headers=headers), timeout=60) as r:
                return json.load(r)
        except error.HTTPError as e:
            if e.code == 404:
                return None
            print(f"  HTTP {e.code} (try {attempt}/3)")
        except error.URLError as e:
            print(f"  Network error: {e.reason} (try {attempt}/3)")
        time.sleep(3 * attempt)
    return None


def pick_price(card):
    """Returns the TCGplayer market price (USD) for a card, or None."""
    prices = (card.get("tcgplayer") or {}).get("prices") or {}
    order = VARIANT_ORDER + [k for k in prices if k not in VARIANT_ORDER]
    for variant in order:
        p = prices.get(variant) or {}
        value = p.get("market") or p.get("mid")
        if value:
            return float(value)
    return None


def fetch_card(card_id):
    res = api_get(f"/cards/{card_id}")
    if not res:
        return None
    return pick_price(res["data"])


def fetch_set_total(set_id):
    """Adds up the market price of every card in the set."""
    total, page, counted = 0.0, 1, 0
    while True:
        res = api_get("/cards", {
            "q": f"set.id:{set_id}",
            "page": page,
            "pageSize": 250,
            "select": "id,tcgplayer",
        })
        if not res or not res.get("data"):
            break
        for card in res["data"]:
            price = pick_price(card)
            if price:
                total += price
                counted += 1
        if len(res["data"]) < 250:
            break
        page += 1
    return round(total, 2) if counted else None


def read_history():
    if not HISTORY.exists():
        return []
    with open(HISTORY, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_history(rows):
    HISTORY.parent.mkdir(exist_ok=True)
    rows.sort(key=lambda r: (r["date"], r["type"], r["id"]))
    with open(HISTORY, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


# Used only by --demo (no internet): set id -> API series name
DEMO_SERIES = {"base1": "Base", "swsh7": "Sword & Shield", "sv3pt5": "Scarlet & Violet"}


def set_series_map(sample=False):
    """Maps set id -> series name from the API (e.g. 'sv3pt5' -> 'Scarlet & Violet')."""
    if sample:
        return DEMO_SERIES
    mapping, page = {}, 1
    while True:
        res = api_get("/sets", {"select": "id,series", "page": page, "pageSize": 250})
        if not res or not res.get("data"):
            break
        mapping.update({x["id"]: x["series"] for x in res["data"]})
        if len(res["data"]) < 250:
            break
        page += 1
    if mapping:
        SETS_CACHE.parent.mkdir(exist_ok=True)
        SETS_CACHE.write_text(json.dumps(mapping), encoding="utf-8")
        return mapping
    if SETS_CACHE.exists():  # API down: reuse the last known mapping
        return json.loads(SETS_CACHE.read_text(encoding="utf-8"))
    return {}


def era_for(series_name, eras):
    for era in eras:
        if series_name in era["series"]:
            return era["id"]
    return "other"


def build_data_js(rows, sample=False):
    eras = json.loads(ERAS.read_text(encoding="utf-8"))
    set_series = set_series_map(sample)
    series = {}
    for r in rows:
        key = f"{r['type']}:{r['id']}"
        set_id = r["id"] if r["type"] == "set" else r["id"].rsplit("-", 1)[0]
        era = era_for(set_series.get(set_id), eras)
        s = series.setdefault(key, {"type": r["type"], "id": r["id"], "label": r["label"], "era": era, "points": []})
        s["label"] = r["label"]  # latest label wins
        s["points"].append([r["date"], float(r["price"])])
    payload = {
        "updated": datetime.now().strftime("%Y-%m-%d"),
        "sample": sample,
        "eras": [{"id": e["id"], "name": e["name"], "years": e["years"]} for e in eras]
                + [{"id": "other", "name": "Other", "years": ""}],
        "series": list(series.values()),
    }
    DATA_JS.parent.mkdir(exist_ok=True)
    DATA_JS.write_text("window.PRICE_DATA = " + json.dumps(payload) + ";\n", encoding="utf-8")


def run_real():
    watch = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    new_rows = []

    for card in watch.get("cards", []):
        print(f"Card: {card['label']}")
        price = fetch_card(card["id"])
        if price is None:
            print(f"  ! No price found for '{card['id']}'. Check the ID in watchlist.json.")
            continue
        new_rows.append({"date": today, "type": "card", "id": card["id"], "label": card["label"], "price": price})

    for s in watch.get("sets", []):
        print(f"Set: {s['label']}")
        total = fetch_set_total(s["id"])
        if total is None:
            print(f"  ! No prices found for set '{s['id']}'. Check the ID in watchlist.json.")
            continue
        new_rows.append({"date": today, "type": "set", "id": s["id"], "label": s["label"], "price": total})

    if not new_rows:
        print("Nothing fetched, so nothing was saved.")
        sys.exit(1)

    # Re-running on the same day replaces that day's rows instead of duplicating them
    replaced = {(r["type"], r["id"]) for r in new_rows}
    rows = [r for r in read_history() if not (r["date"] == today and (r["type"], r["id"]) in replaced)]
    rows.extend(new_rows)
    write_history(rows)
    build_data_js(rows)
    print(f"Saved {len(new_rows)} prices for {today}.")


def run_demo():
    """Fake 60 days of history so you can preview the dashboard. Does NOT touch history.csv."""
    watch = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    random.seed(7)
    rows = []
    start = date.today() - timedelta(days=59)
    items = [("card", c) for c in watch.get("cards", [])] + [("set", s) for s in watch.get("sets", [])]
    for kind, item in items:
        price = random.uniform(40, 400) if kind == "card" else random.uniform(500, 1500)
        for d in range(60):
            price = max(1, price * (1 + random.uniform(-0.03, 0.035)))
            rows.append({
                "date": (start + timedelta(days=d)).isoformat(),
                "type": kind, "id": item["id"], "label": item["label"], "price": round(price, 2),
            })
    build_data_js(rows, sample=True)
    print("Demo data written to data/data.js")


if __name__ == "__main__":
    run_demo() if "--demo" in sys.argv else run_real()
