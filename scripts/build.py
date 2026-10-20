#!/usr/bin/env python3
"""Build archive pages and the archive index from content/*.json and data/*.json.

- content/<date>.json  → /<date>/index.html (a copy of index.html pinned to that date) and listed in archive/index.json
- content/latest.json  → copy of the newest dated content file
No dependencies beyond the standard library.
"""
import json, os, re, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def nails(data):
    n = k = 0
    for sid in ("ust10y", "usdkrw", "brent"):
        pts = [p for p in (data.get("series", {}).get(sid, {}).get("points") or []) if isinstance(p.get("value"), (int, float))]
        if len(pts) >= 21:
            k += 1
            if pts[-1]["value"] > pts[-1 - min(60, len(pts) - 1)]["value"]:
                n += 1
    return n if k == 3 else None


def main():
    cdir, ddir = os.path.join(ROOT, "content"), os.path.join(ROOT, "data")
    dates = sorted(f[:-5] for f in os.listdir(cdir) if DATE.match(f))
    if not dates:
        raise SystemExit("no content/<date>.json files")
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        template = f.read()
    index = []
    for d in dates:
        with open(os.path.join(cdir, d + ".json"), encoding="utf-8") as f:
            c = json.load(f)
        dpath = os.path.join(ddir, d + ".json")
        data = json.load(open(dpath)) if os.path.exists(dpath) else {}
        index.append({"date": d, "headline": c.get("headline"), "regime": (c.get("regime") or {}).get("value"), "nails": nails(data)})
        page = template.replace('data-date="latest"', f'data-date="{d}"', 1).replace("<title>IEUM Daily Investment Trends</title>", f"<title>IEUM Daily Investment Trends — {d}</title>", 1)
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
        with open(os.path.join(ROOT, d, "index.html"), "w", encoding="utf-8") as f:
            f.write(page)
    index.sort(key=lambda r: r["date"], reverse=True)
    os.makedirs(os.path.join(ROOT, "archive"), exist_ok=True)
    with open(os.path.join(ROOT, "archive", "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    shutil.copyfile(os.path.join(cdir, dates[-1] + ".json"), os.path.join(cdir, "latest.json"))
    # data/latest.json follows the newest dated data file if the fetch did not already write it
    ddates = sorted(f[:-5] for f in os.listdir(ddir) if DATE.match(f))
    if ddates:
        shutil.copyfile(os.path.join(ddir, ddates[-1] + ".json"), os.path.join(ddir, "latest.json"))
    print("built %d archive page(s); latest = %s" % (len(dates), dates[-1]))


if __name__ == "__main__":
    main()
