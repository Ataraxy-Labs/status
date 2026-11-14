"""One round of checks for status.useland.dev's data: each monitor once, appended to data/history/<id>.csv
(unix time, HTTP status, milliseconds, 1 if healthy), then data/summary.json rebuilt from the whole history.
A monitor is healthy when it answers with its expected status (and, if set, its body contains the expected text)
within 15 s. Run from outside land's own machines, so an outage of land's host is seen."""
import json, os, ssl, time, urllib.request, urllib.error

D = "data"
MON = json.load(open("monitors.json"))
os.makedirs(f"{D}/history", exist_ok=True)
now = int(time.time())

def check(m):
    req = urllib.request.Request(m["url"], method=m.get("method", "GET"), headers={"User-Agent": "useland-status/1"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl.create_default_context()) as r:
            code, body = r.status, (r.read(65536) if m.get("contains") else b"")
    except urllib.error.HTTPError as e:
        code, body = e.code, b""
    except Exception:
        return 0, int((time.time() - t0) * 1000), False
    ms = int((time.time() - t0) * 1000)
    ok = code == m["expect"] and (not m.get("contains") or m["contains"].encode() in body)
    return code, ms, ok

for m in MON:
    code, ms, ok = check(m)
    if not ok:  # one retry after 20 s, so a single dropped packet is not an outage
        time.sleep(20)
        code, ms, ok = check(m)
    with open(f"{D}/history/{m['id']}.csv", "a") as f:
        f.write(f"{now},{code},{ms},{int(ok)}\n")

def rows(i):
    try:
        return [tuple(int(x) for x in l.split(",")) for l in open(f"{D}/history/{i}.csv") if l.strip()]
    except FileNotFoundError:
        return []

def pct(rs):
    return None if not rs else round(100 * sum(r[3] for r in rs) / len(rs), 3)

day = 86400
today0 = now - now % day
out = {"updated": now, "monitors": []}
for m in MON:
    rs = rows(m["id"])
    days = []
    for k in range(89, -1, -1):
        s = today0 - k * day
        b = [r for r in rs if s <= r[0] < s + day]
        days.append({"day": s, "checks": len(b), "up": sum(r[3] for r in b)})
    last = rs[-1] if rs else None
    out["monitors"].append({
        "id": m["id"], "name": m["name"], "url": m["url"],
        "since": rs[0][0] if rs else None, "checks": len(rs),
        "up_now": bool(last and last[3]), "last_ms": last[2] if last else None, "last_code": last[1] if last else None,
        "uptime_24h": pct([r for r in rs if r[0] >= now - day]),
        "uptime_7d": pct([r for r in rs if r[0] >= now - 7 * day]),
        "uptime_30d": pct([r for r in rs if r[0] >= now - 30 * day]),
        "uptime_all": pct(rs), "days": days,
    })
json.dump(out, open(f"{D}/summary.json", "w"), separators=(",", ":"))
print(json.dumps([[m["id"], m["up_now"], m["last_code"], m["last_ms"]] for m in out["monitors"]]))
