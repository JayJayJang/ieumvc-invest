#!/usr/bin/env python3
"""Rank the watchlist universe by what happened in the previous trading sessions.

Reads the "Watchlist universe" table in README.md, pulls KRX regular-session daily
quotes and investor data from Daum Finance, checks the newest content/<date>.json
catalyst calendar, and prints each name with a suggested priority (HIGH / MEDIUM / LOW)
and the triggers behind it, highest first. The brief writer adds event triggers the
data cannot see (new disclosures, trial readouts, deals, press) and may raise a rank,
never lower one the data set.

Usage: python scripts/watch.py [--json]
No dependencies beyond the standard library.
"""
import datetime as dt, json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (compatible; ieumvc-watch/1.0)"
RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
MAX_HIGH = 3  # HIGH stays meaningful: at most this many, unless forced by a near catalyst or a 10% day


def universe():
    rows = []
    for line in open(os.path.join(ROOT, "README.md"), encoding="utf-8"):
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*(\d{6})\s*\|\s*(KOSPI|KOSDAQ)\s*\|", line)
        if m:
            rows.append({"name": m.group(1), "code": m.group(2), "market": m.group(3)})
    return rows


def get(url, code, tries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": f"https://finance.daum.net/quotes/A{code}"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)["data"]
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def catalysts():
    cdir = os.path.join(ROOT, "content")
    files = sorted(f for f in os.listdir(cdir) if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", f))
    c = json.load(open(os.path.join(cdir, files[-1]), encoding="utf-8")) if files else {}
    return c.get("catalysts") or []


def bdays(a, b):
    """Weekdays from date a (exclusive) to date b (inclusive)."""
    n, d = 0, a
    while d < b:
        d += dt.timedelta(days=1)
        n += d.weekday() < 5
    return n


def done(row, now):
    """True for a finished regular session: traded, and not today's session before 16:00 KST."""
    if not row.get("accTradeVolume"):
        return False
    return row["date"][:10] != now.date().isoformat() or now.hour >= 16


def assess(u, cats, now):
    today = now.date()
    code = u["code"]
    days = get(f"https://finance.daum.net/api/quote/A{code}/days?symbolCode=A{code}&page=1&perPage=25&pagination=true", code)
    inv = get(f"https://finance.daum.net/api/investor/days?symbolCode=A{code}&page=1&perPage=6", code)
    # keep finished sessions only: no zero-volume placeholders, no intraday rows
    days = [d for d in days if done(d, now)]
    inv = [d for d in inv if done(d, now)]
    last = days[0]
    close = last["tradePrice"]
    chg1 = last["changeRate"] * 100
    chg3 = (close / days[3]["tradePrice"] - 1) * 100 if len(days) > 3 else 0.0
    vols = [d["accTradeVolume"] for d in days[1:21]]
    vratio = last["accTradeVolume"] / (sum(vols) / len(vols)) if vols else 0.0
    own = [d["foreignOwnSharesRate"] * 100 for d in inv]
    own3 = own[0] - own[3] if len(own) > 3 else 0.0
    streak, sign = 0, 0
    for d in inv:
        s = (d["foreignStraightPurchaseVolume"] > 0) - (d["foreignStraightPurchaseVolume"] < 0)
        if s == 0 or (sign and s != sign):
            break
        sign, streak = s, streak + 1
    hi, med, force = [], [], False
    if abs(chg1) >= 10: force = True
    if abs(chg1) >= 5: hi.append(f"1-day move {chg1:+.2f}%")
    elif abs(chg1) >= 2.5: med.append(f"1-day move {chg1:+.2f}%")
    if abs(chg3) >= 10: hi.append(f"3-session move {chg3:+.1f}%")
    elif abs(chg3) >= 5: med.append(f"3-session move {chg3:+.1f}%")
    if vratio >= 2: hi.append(f"volume {vratio:.1f}x 20-session average")
    elif vratio >= 1.5: med.append(f"volume {vratio:.1f}x 20-session average")
    if abs(own3) >= 0.5: hi.append(f"foreign ownership {own3:+.2f}pp over 3 sessions")
    elif abs(own3) >= 0.25: med.append(f"foreign ownership {own3:+.2f}pp over 3 sessions")
    if streak >= 5: hi.append(f"foreign net {'buying' if sign > 0 else 'selling'} {streak} sessions running")
    elif streak >= 3: med.append(f"foreign net {'buying' if sign > 0 else 'selling'} {streak} sessions running")
    for c in cats:
        scope = ((c.get("scope") or {}).get("en") or "") + " " + ((c.get("event") or {}).get("en") or "")
        if u["name"].split()[0].lower() not in scope.lower():
            continue
        try:
            n = bdays(today, dt.date.fromisoformat(c["date"]))
        except (KeyError, ValueError):
            continue
        ev = (c.get("event") or {}).get("en", "")
        if 0 <= n <= 5:
            hi.append(f"dated catalyst in {n} trading day(s): {c['date']} {ev}")
            force = True
        elif 0 <= n <= 20: med.append(f"dated catalyst in {n} trading days: {c['date']} {ev}")
    score = 2 * len(hi) + len(med)
    return {**u, "session": last["date"][:10], "close": close, "chg1": round(chg1, 2), "chg3": round(chg3, 2),
            "vol_ratio": round(vratio, 2), "foreign_own": round(own[0], 2) if own else None,
            "own_3s_pp": round(own3, 2), "score": score, "force": force, "triggers": hi + med}


def main():
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    cats, out = catalysts(), []
    for u in universe():
        try:
            out.append(assess(u, cats, now))
        except Exception as e:  # keep going; report the gap instead of guessing
            out.append({**u, "priority": None, "error": str(e), "triggers": []})
    # score: 2 per strong trigger, 1 per moderate one. Top MAX_HIGH scorers with >= 2 points are HIGH,
    # plus any name forced by a catalyst within 5 trading days or a 10% day; other scorers MEDIUM; 0 is LOW.
    ok = sorted((r for r in out if "error" not in r), key=lambda r: (-r["force"], -r["score"], -abs(r["chg1"])))
    for i, r in enumerate(ok):
        r["priority"] = "HIGH" if r["force"] or (i < MAX_HIGH and r["score"] >= 2) else "MEDIUM" if r["score"] else "LOW"
    out = sorted(ok, key=lambda r: (-RANK[r["priority"]], -r["score"], -abs(r["chg1"]))) + [r for r in out if "error" in r]
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    for r in out:
        if r.get("error"):
            print(f"??     {r['name']} ({r['code']}): not found — {r['error']}")
            continue
        print(f"{r['priority']:<6} [{r['score']}] {r['name']} ({r['code']}) close {r['close']:,.0f} on {r['session']} "
              f"{r['chg1']:+.2f}% · 3s {r['chg3']:+.1f}% · vol {r['vol_ratio']}x · foreign {r['foreign_own']}% ({r['own_3s_pp']:+.2f}pp)")
        for t in r["triggers"]:
            print(f"         - {t}")


if __name__ == "__main__":
    main()
