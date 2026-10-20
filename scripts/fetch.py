#!/usr/bin/env python3
"""Pull the day's market data from Alpha Vantage into data/<KST date>.json and data/latest.json.

Eight calls, one at a time (free key: 1 request/second, 25/day):
  TREASURY_YIELD daily 10year · FX_DAILY USD/KRW · BRENT daily · GLOBAL_QUOTE × SPY, XBI, EWY, TLT, UUP
Set ALPHAVANTAGE_API_KEY in the environment (GitHub Actions: repository secret).
Stdlib only.
"""
import json, os, sys, time, datetime, urllib.request, urllib.parse

KEY = os.environ.get("ALPHAVANTAGE_API_KEY")
if not KEY:
    sys.exit("ALPHAVANTAGE_API_KEY is not set")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = os.environ.get("BRIEF_DATE") or datetime.datetime.now(KST).strftime("%Y-%m-%d")
QUOTES = [("SPY", "S&P 500 (US beta)"), ("XBI", "US biotech (XBI)"), ("EWY", "Korea (EWY, USD terms)"), ("TLT", "Long Treasuries"), ("UUP", "US dollar index")]
KEEP = 260  # trading days of history kept per series


def call(params, tries=3):
    url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode(dict(params, apikey=KEY, datatype="json"))
    last = None
    for i in range(tries):
        time.sleep(1.5 if i == 0 else 20)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                a = json.load(r)
        except Exception as e:  # network
            last = e; continue
        if isinstance(a, dict) and ("Note" in a or "Information" in a) and len(a) == 1:
            last = RuntimeError(a.get("Note") or a.get("Information")); continue
        if isinstance(a, dict) and "Error Message" in a:
            raise RuntimeError(a["Error Message"])
        return a
    raise RuntimeError(f"{params.get('function')} failed after {tries} tries: {last}")


def series(a):
    rows = [{"date": r["date"], "value": float(r["value"])} for r in a.get("data", []) if r.get("value") not in (None, "", ".")]
    rows.sort(key=lambda r: r["date"])
    return rows[-KEEP:]


def main():
    failed = []
    out = {"as_of": datetime.datetime.now(KST).isoformat(timespec="minutes"),
           "source": "Alpha Vantage — FRED 10Y CMT (daily), FX daily USD/KRW, EIA Brent (daily), end-of-day quotes; fetched by the workflow",
           "series": {}, "quotes": []}
    try:
        out["series"]["ust10y"] = {"label": "US 10Y Treasury yield", "unit": "%", "points": series(call({"function": "TREASURY_YIELD", "interval": "daily", "maturity": "10year"}))}
    except Exception as e:
        failed.append(f"ust10y: {e}")
    try:
        a = call({"function": "FX_DAILY", "from_symbol": "USD", "to_symbol": "KRW", "outputsize": "compact"})
        ts = a.get("Time Series FX (Daily)", {})
        pts = sorted([{"date": d, "value": float(v["4. close"])} for d, v in ts.items()], key=lambda r: r["date"])
        out["series"]["usdkrw"] = {"label": "USD/KRW", "unit": "KRW", "points": pts[-KEEP:]}
    except Exception as e:
        failed.append(f"usdkrw: {e}")
    try:
        out["series"]["brent"] = {"label": "Brent crude", "unit": "USD/bbl", "points": series(call({"function": "BRENT", "interval": "daily"}))}
    except Exception as e:
        failed.append(f"brent: {e}")
    for sym, name in QUOTES:
        try:
            q = call({"function": "GLOBAL_QUOTE", "symbol": sym}).get("Global Quote", {})
            if not q:
                raise RuntimeError("empty quote")
            out["quotes"].append({"symbol": q["01. symbol"], "name": name, "price": float(q["05. price"]),
                                  "change_pct": float(str(q["10. change percent"]).rstrip("%")), "prev_close": float(q["08. previous close"]), "day": q["07. latest trading day"]})
        except Exception as e:
            failed.append(f"{sym}: {e}")

    # Carry forward yesterday's series for anything that failed, so the page never goes blank.
    prev_path = os.path.join(ROOT, "data", "latest.json")
    if failed and os.path.exists(prev_path):
        with open(prev_path) as f:
            prev = json.load(f)
        for k, v in prev.get("series", {}).items():
            out["series"].setdefault(k, dict(v, carried_from=prev.get("as_of")))
        if not out["quotes"]:
            out["quotes"] = [dict(q, carried_from=prev.get("as_of")) for q in prev.get("quotes", [])]
    if failed:
        out["failed"] = failed
        print("WARN:", *failed, sep="\n  ")

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    for name in (TODAY + ".json", "latest.json"):
        with open(os.path.join(ROOT, "data", name), "w") as f:
            json.dump(out, f, indent=1)
    print("wrote data/%s.json and data/latest.json (%d series, %d quotes)" % (TODAY, len(out["series"]), len(out["quotes"])))


if __name__ == "__main__":
    main()
