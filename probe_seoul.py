"""서울 문화행사 확인 2 (한 번 쓰고 지움)"""
import json, os, urllib.request, urllib.parse, datetime
K = os.environ["SEOUL_KEY"].strip()
def get(path):
    u = f"http://openapi.seoul.go.kr:8088/{K}/json/" + path
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "airang-probe"}), timeout=60) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"_err": type(e).__name__}
today = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=9)).date().isoformat()
idx = []
for a in range(1, 20001, 1000):
    rows = (get(f"culturalEventInfo/{a}/{a+999}/").get("culturalEventInfo") or {}).get("row") or []
    if not rows: break
    for i, r in enumerate(rows):
        if str(r.get("END_DATE", ""))[:10] >= today: idx.append(a + i)
    print(a, "첫 등록일", rows[0].get("RGSTDATE"), "끝", rows[-1].get("RGSTDATE"))
print("진행중 위치: 최소", min(idx), "최대", max(idx), "개수", len(idx))
for p in (f"culturalEventInfo/1/5/%20/%20/{today}", f"culturalEventInfo/1/5/ / /{today}"):
    d = get(urllib.parse.quote(p, safe="/%"))
    b = d.get("culturalEventInfo") or {}
    print("DATE 거르기:", b.get("list_total_count"), [r.get("DATE") for r in (b.get("row") or [])][:3], d.get("RESULT") or d.get("_err"))
