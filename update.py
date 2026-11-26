"""Haalt elke dag het nieuws van Forex Factory op en werkt ff.json en rates.json bij.
Draait automatisch via GitHub Actions (.github/workflows/update.yml)."""
import json, sys, urllib.request, datetime, re

FEEDS = ["https://nfs.faireconomy.media/ff_calendar_thisweek.json",
         "https://nfs.faireconomy.media/ff_calendar_nextweek.json"]
MON = ["jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"]
# Titel bij Forex Factory -> code van de centrale bank in rates.json
RATE_TITLES = {"USD": ("Fed", r"Federal Funds Rate"), "EUR": ("ECB", r"Main Refinancing Rate|Deposit Facility Rate"),
               "GBP": ("BoE", r"Official Bank Rate"), "JPY": ("BoJ", r"BOJ Policy Rate"),
               "AUD": ("RBA", r"Cash Rate"), "CAD": ("BoC", r"Overnight Rate"),
               "CHF": ("SNB", r"SNB Policy Rate"), "NZD": ("RBNZ", r"Official Cash Rate")}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (forex-waarschuwingen)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def today_nl():
    d = datetime.date.today()
    return f"{d.day} {MON[d.month-1]} {d.year}"

def main(test_files=None):
    new = []
    for src in (test_files or FEEDS):
        try:
            data = json.load(open(src)) if test_files else fetch(src)
            new += [x for x in data if isinstance(x, dict)]
            print("Opgehaald:", src, len(data))
        except Exception as e:
            print("Niet gelukt:", src, e)
    keep = [{k: str(x.get(k, "") or "") for k in ("title", "country", "date", "impact", "forecast", "previous")}
            for x in new if x.get("impact") in ("High", "Medium", "Low", "Holiday") and x.get("title") and x.get("date")]
    if not keep:
        print("Geen nieuws gevonden, er verandert niets."); return
    try:
        old = json.load(open("ff.json")).get("items", [])
    except Exception:
        old = []
    now = datetime.datetime.now(datetime.timezone.utc)
    key = lambda x: (x["title"], x["country"], x["date"])
    seen = {key(x) for x in keep}
    for x in old:  # oude berichten van de laatste 14 dagen bewaren
        try:
            t = datetime.datetime.fromisoformat(x["date"])
        except Exception:
            continue
        if key(x) not in seen and (now - t).days <= 14:
            keep.append(x); seen.add(key(x))
    keep.sort(key=lambda x: x["date"])
    json.dump({"at": today_nl(), "items": keep}, open("ff.json", "w"), ensure_ascii=False)
    print("ff.json:", len(keep), "berichten")

    update_rates(keep)

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (forex-waarschuwingen)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def last_csv_value(text, col=1, sep=","):
    val = None
    for line in text.splitlines():
        p = [c.strip().strip('"') for c in line.split(sep)]
        if len(p) > col:
            try: val = float(p[col])
            except ValueError: pass
    return val

def fed():
    u = last_csv_value(get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARU&cosd=2026-01-01"))
    l = last_csv_value(get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARL&cosd=2026-01-01"))
    return (u + l) / 2, f"{l:.2f}–{u:.2f}%".replace(".", ",")
def ecb():
    return last_csv_value(get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=ECBDFR&cosd=2026-01-01")), ""
def boe():
    d = datetime.date.today() - datetime.timedelta(days=60)
    url = ("https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom="
           + d.strftime("%d/%b/%Y") + "&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y")
    return last_csv_value(get(url)), ""
def boc():
    j = json.loads(get("https://www.bankofcanada.ca/valet/observations/V39079/json?recent=1"))
    return float(j["observations"][-1]["V39079"]["v"]), ""
def snb():
    val = None
    for line in get("https://data.snb.ch/api/cube/snbgwdzid/data/csv/en").splitlines():
        p = [c.strip().strip('"') for c in line.split(";")]
        if len(p) >= 3 and p[1] == "LZ" and p[2]:
            try: val = float(p[2])
            except ValueError: pass
    return val, ""
def rba():
    col, val = None, None
    for line in get("https://www.rba.gov.au/statistics/tables/csv/f1-data.csv").splitlines():
        p = [c.strip().strip('"') for c in line.split(",")]
        if p and p[0] == "Series ID" and "FIRMMCRTD" in p:
            col = p.index("FIRMMCRTD")
        elif col is not None and len(p) > col and p[col]:
            try: val = float(p[col])
            except ValueError: pass
    return val, ""
SOURCES = {"Fed": fed, "ECB": ecb, "BoE": boe, "BoC": boc, "SNB": snb, "RBA": rba}

def from_ff(keep, code):
    """Reserve: bij een komend rentebesluit zet Forex Factory de huidige rente bij 'previous'."""
    cur = next(c for c, (k, _) in RATE_TITLES.items() if k == code)
    pat = RATE_TITLES[cur][1]
    for x in keep:
        if x["country"] == cur and re.search(pat, x["title"]):
            m = re.match(r"^\s*(-?\d+(?:\.\d+)?)%", x["previous"])
            if m:
                v = float(m.group(1))
                if code == "Fed": return v - 0.125, f"{v-0.25:.2f}–{v:.2f}%".replace(".", ",")
                if code == "ECB" and "Main Refinancing" in x["title"]: return round(v - 0.15, 2), ""
                return v, ""
    return None, ""

def update_rates(keep):
    try:
        rates = json.load(open("rates.json"))
    except Exception:
        return
    changed = False
    for b in rates.get("banks", []):
        code, val, txt = b["k"], None, ""
        if code in SOURCES:
            try:
                val, txt = SOURCES[code]()
            except Exception as e:
                print("Bron niet bereikbaar:", code, e)
        if val is None:
            val, txt = from_ff(keep, code)
        if val is None or not (-2 < val < 25):
            print("Geen nieuwe rente voor", code); continue
        old = b.get("r")
        if old is None or abs(old - val) > 0.001:
            if old is not None:
                diff = val - old
                b["last"] = (f"+{diff:.2f}" if diff > 0 else f"{diff:.2f}").replace(".", ",") + " op " + today_nl().rsplit(" ", 1)[0]
            b["r"] = round(val, 4)
            if txt: b["txt"] = txt
            print("Rente gewijzigd:", code, old, "->", val); changed = True
    if changed:
        rates["at"] = today_nl()
        json.dump(rates, open("rates.json", "w"), ensure_ascii=False)
    else:
        print("Rentes ongewijzigd")

def update_fx():
    """Wisselkoersen van de ECB (via frankfurter.dev) voor het tabblad Munten."""
    start = (datetime.date.today() - datetime.timedelta(days=100)).isoformat()
    try:
        j = json.loads(get("https://api.frankfurter.dev/v1/" + start + "..?from=EUR&to=USD,GBP,JPY,AUD,CAD,CHF,NZD"))
        cur = ["USD", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
        dates = sorted(d for d, r in j["rates"].items() if all(c in r for c in cur))
        if len(dates) < 10:
            raise ValueError("te weinig koersen")
        fx = {"at": today_nl(), "dates": dates, "rates": {c: [j["rates"][d][c] for d in dates] for c in cur}}
        json.dump(fx, open("fx.json", "w"))
        print("fx.json:", len(dates), "dagen")
    except Exception as e:
        print("Koersen niet bijgewerkt:", e)

NTFY_TOPIC = "forex-waarschuwingen-2f6e3762c8"
DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]

def ntfy(payload):
    req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status

def schedule_alerts(send=ntfy):
    """Plant pushmeldingen in via ntfy.sh, 1 minuut voor elk hoog nieuwsbericht."""
    from zoneinfo import ZoneInfo
    nl = ZoneInfo("Europe/Amsterdam")
    try:
        items = json.load(open("ff.json")).get("items", [])
    except Exception:
        return
    try:
        sent = json.load(open("sent.json"))
    except Exception:
        sent = None
    now = datetime.datetime.now(datetime.timezone.utc)
    if sent is None:
        sent = []
        try:
            send({"topic": NTFY_TOPIC, "title": "Forex-waarschuwingen",
                  "message": "De meldingen staan aan. Je krijgt voortaan 1 minuut voor elk hoog nieuwsbericht een melding.",
                  "tags": ["white_check_mark"]})
        except Exception as e:
            print("Welkomstmelding mislukt:", e)
    keep = []
    for x in items:
        if x.get("impact") != "High":
            continue
        try:
            t = datetime.datetime.fromisoformat(x["date"])
        except Exception:
            continue
        key = x["title"] + "|" + x["country"] + "|" + x["date"] + "|1m"
        alert = t - datetime.timedelta(minutes=1)
        if t < now - datetime.timedelta(days=2):
            continue
        if key in sent:
            keep.append(key); continue
        if t <= now or alert > now + datetime.timedelta(days=2, hours=23):
            continue
        lt = t.astimezone(nl)
        msg = (f"Om {lt:%H:%M} komt {x['title']} ({x['country']}). Dit is hoog nieuws en kan de koers flink bewegen. "
               "Open liever geen nieuwe trade en kijk naar de stop-loss van je open posities.")
        if x.get("forecast"):
            msg += f" Forex Factory verwacht {x['forecast']}."
        payload = {"topic": NTFY_TOPIC, "title": f"Over 1 minuut hoog nieuws ({x['country']})",
                   "message": msg, "priority": 4, "tags": ["warning"]}
        if alert > now + datetime.timedelta(seconds=30):
            payload["delay"] = str(int(alert.timestamp()))
        else:
            payload["title"] = f"Zo meteen hoog nieuws ({x['country']})"
        try:
            send(payload); keep.append(key)
            print("Melding ingepland:", key, "om", alert.astimezone(nl).strftime("%d-%m %H:%M"))
        except Exception as e:
            print("Melding mislukt:", key, e)
    json.dump(keep, open("sent.json", "w"))

if __name__ == "__main__":
    main(sys.argv[1:] or None)
    if not sys.argv[1:]:
        update_fx()
        schedule_alerts()
