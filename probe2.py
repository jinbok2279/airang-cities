"""새 도시 14곳 열기 전 확인 (한 번 쓰고 지움) — 키 값은 찍지 않음"""
import json, os, urllib.parse, urllib.request, re
def get(url, params, raw=False):
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "airang-probe"}), timeout=60) as r:
            t = r.read().decode("utf-8", "replace")
        return t if raw else json.loads(t)
    except Exception as e:
        return {"_err": str(e)[:120]}
LIB = os.environ["LIB_KEY"]; NEIS = os.environ["NEIS_KEY"]; WK = urllib.parse.unquote(os.environ["WEATHER_KEY"])
print("== 정보나루 경기(31) 세부지역")
for c in range(31010, 31330, 10):
    for cc in ([c] if c % 10 == 0 else []) + [c + 1, c + 2, c + 3, c + 4] if False else [c]:
        d = get("https://data4library.kr/api/libSrch", {"authKey": LIB, "format": "json", "region": 31, "dtl_region": cc, "pageNo": 1, "pageSize": 3})
        r = d.get("response", {}) if isinstance(d, dict) else {}
        libs = [x.get("lib", x) for x in (r.get("libs") or [])]
        if r.get("numFound"): print(" ", cc, r.get("numFound"), (libs[0].get("address", "")[:16] if libs else ""))
for cc in (31271, 31272, 31273, 31091, 31092):
    d = get("https://data4library.kr/api/libSrch", {"authKey": LIB, "format": "json", "region": 31, "dtl_region": cc, "pageNo": 1, "pageSize": 3})
    r = d.get("response", {}) if isinstance(d, dict) else {}
    libs = [x.get("lib", x) for x in (r.get("libs") or [])]
    if r.get("numFound"): print("  sub", cc, r.get("numFound"), (libs[0].get("address", "")[:16] if libs else ""))
print("== 정보나루 서울 빠진 구")
for cc in (11080, 11160, 11200, 11220):
    d = get("https://data4library.kr/api/libSrch", {"authKey": LIB, "format": "json", "region": 11, "dtl_region": cc, "pageNo": 1, "pageSize": 3})
    r = d.get("response", {}) if isinstance(d, dict) else {}
    libs = [x.get("lib", x) for x in (r.get("libs") or [])]
    print(" ", cc, r.get("numFound"), (libs[0].get("address", "")[:16] if libs else ""), str(d)[:100] if not r else "")
print("== 학원 수 (행정구역명)")
for z, o in (("남양주시", "J10"), ("안산시", "J10"), ("시흥시", "J10"), ("파주시", "J10"), ("김포시", "J10"), ("의정부시", "J10"), ("광주시", "J10"), ("하남시", "J10"),
             ("서초구", "B10"), ("송파구", "B10"), ("강동구", "B10"), ("광진구", "B10"), ("마포구", "B10"), ("성동구", "B10")):
    d = get("https://open.neis.go.kr/hub/acaInsTiInfo", {"KEY": NEIS, "Type": "json", "pIndex": 1, "pSize": 1, "ATPT_OFCDC_SC_CODE": o, "ADMST_ZONE_NM": z})
    try: print(" ", z, d["acaInsTiInfo"][0]["head"][0]["list_total_count"])
    except Exception: print(" ", z, str(d)[:100])
print("== 에어코리아 경기 측정소")
d = get("http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnList", {"serviceKey": WK, "returnType": "json", "numOfRows": 300, "pageNo": 1, "addr": "경기"})
try:
    for i in d["response"]["body"]["items"]:
        m = re.search(r"경기도?\s*(\S+시|\S+군)", i.get("addr", ""))
        print("  ", m.group(1) if m else "?", "|", i["stationName"])
except Exception:
    print(str(d)[:300])
    d = get("http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty", {"serviceKey": WK, "returnType": "json", "numOfRows": 200, "pageNo": 1, "sidoName": "경기", "ver": "1.3"})
    try: print(" ", [i["stationName"] for i in d["response"]["body"]["items"]])
    except Exception: print(str(d)[:200])
