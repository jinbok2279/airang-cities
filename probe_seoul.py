"""서울 문화행사·공공예약 확인 (한 번 쓰고 지움) — 키 값·주소는 찍지 않음"""
import json, os, urllib.request, collections, datetime
K = os.environ["SEOUL_KEY"].strip()
def get(svc, a, b, extra=""):
    u = f"http://openapi.seoul.go.kr:8088/{K}/json/{svc}/{a}/{b}/{extra}"
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "airang-probe"}), timeout=60) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"_err": type(e).__name__ + " " + str(e)[:80].replace(K, "***")}
today = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date().isoformat()
print("키 길이", len(K), "오늘", today)
for svc in ("culturalEventInfo", "ListPublicReservationCulture", "ListPublicReservationEducation", "ListPublicReservationSport"):
    d = get(svc, 1, 1)
    if "_err" in d: print(svc, d); continue
    body = d.get(svc) or {}
    print("==", svc, "전체", body.get("list_total_count"), (body.get("RESULT") or d.get("RESULT")))
    rows = []
    tot = body.get("list_total_count") or 0
    for a in range(1, min(tot, 6000) + 1, 1000):
        rows += (get(svc, a, a + 999).get(svc) or {}).get("row") or []
    if not rows: continue
    print("  칸:", ", ".join(rows[0].keys()))
    print("  예:", json.dumps({k: str(v)[:40] for k, v in rows[0].items()}, ensure_ascii=False)[:900])
    if svc == "culturalEventInfo":
        live = [r for r in rows if str(r.get("END_DATE", ""))[:10] >= today]
        kid = [r for r in live if any(w in (r.get("USE_TRGT", "") + r.get("TITLE", "") + r.get("CODENAME", "")) for w in ("어린이", "아동", "가족", "초등", "유아", "청소년", "누구나", "전체"))]
        print("  진행중·예정", len(live), "아이 관련", len(kid))
        print("  구별(아이 관련):", dict(collections.Counter(r.get("GUNAME") for r in kid).most_common(30)))
        print("  분류:", dict(collections.Counter(r.get("CODENAME") for r in kid).most_common(15)))
        print("  대상 예:", list(collections.Counter(r.get("USE_TRGT") for r in kid).most_common(10)))
    else:
        live = [r for r in rows if r.get("SVCSTATNM") in ("접수중", "안내중", "예약마감", "접수종료") or True]
        print("  상태:", dict(collections.Counter(r.get("SVCSTATNM") for r in rows)))
        open_ = [r for r in rows if r.get("SVCSTATNM") in ("접수중", "안내중")]
        print("  분류:", dict(collections.Counter(r.get("MINCLASSNM") for r in open_).most_common(15)))
        print("  구별(접수중·안내중):", dict(collections.Counter(r.get("AREANM") for r in open_).most_common(30)))
        print("  대상 예:", list(collections.Counter(r.get("USETGTINFO") for r in open_).most_common(8)))
