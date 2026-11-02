import json, os, urllib.parse, urllib.request, collections, re
LIB = os.environ["LIB_KEY"]; WK = urllib.parse.unquote(os.environ["WEATHER_KEY"])
def get(url, params):
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "airang-probe"}), timeout=60) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"_err": str(e)[:100]}
print("== 정보나루 인천 전체(세부지역 없이)")
d = get("https://data4library.kr/api/libSrch", {"authKey": LIB, "format": "json", "region": 23, "pageNo": 1, "pageSize": 500})
libs = [x.get("lib", x) for x in (d.get("response", {}).get("libs") or [])]
c = collections.Counter((re.search(r"인천광역시\s+(\S+[구군])", l.get("address", "")) or [None, "?"])[1] for l in libs)
print(" ", len(libs), dict(c))
print("  미추홀:", [l.get("libName") for l in libs if "미추홀" in l.get("address", "")][:15])
print("== 전국도서관표준데이터 (공공데이터포털)")
for sg in ("계양구", "미추홀구", "남동구"):
    d = get("http://api.data.go.kr/openapi/tn_pubr_public_lbrry_api", {"serviceKey": WK, "type": "json", "pageNo": 1, "numOfRows": 100, "ctprvnNm": "인천광역시", "signguNm": sg})
    try:
        items = d["response"]["body"]["items"]; print(" ", sg, len(items), [i.get("lbrryNm") for i in items][:12], list(items[0].keys())[:30] if items else "")
    except Exception: print(" ", sg, str(d)[:200])
