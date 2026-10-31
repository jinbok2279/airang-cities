"""서울 구 열기 전 확인 (한 번 쓰고 지울 도구) — 키 값은 출력하지 않고 개수·이름만 찍는다."""
import json, os, urllib.parse, urllib.request, collections, re
def get(url, params, key_name=None, raw=False):
    try:
        u = url + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "airang-probe"}), timeout=60) as r:
            t = r.read().decode("utf-8", "replace")
        return t if raw else json.loads(t)
    except Exception as e:
        return {"_err": str(e)[:150]}
NEIS = os.environ.get("NEIS_KEY", ""); LIB = os.environ.get("LIB_KEY", ""); KIN = os.environ.get("KINDER_KEY", "")
W = os.environ.get("WEATHER_KEY", ""); KOP = os.environ.get("KOPIS_KEY", "")
WK = urllib.parse.unquote(W)
GUS = {"강남구": "11680", "양천구": "11470", "노원구": "11350", "서초구": "11650"}
print("== 1. 나이스 학원 (B10) 행정구역 이름")
d = get("https://open.neis.go.kr/hub/acaInsTiInfo", {"KEY": NEIS, "Type": "json", "pIndex": 1, "pSize": 1000, "ATPT_OFCDC_SC_CODE": "B10"})
rows = (d.get("acaInsTiInfo") or [{}, {}])[1].get("row", []) if isinstance(d, dict) else []
print(" zone 예:", collections.Counter(r.get("ADMST_ZONE_NM") for r in rows).most_common(12))
for g in GUS:
    d = get("https://open.neis.go.kr/hub/acaInsTiInfo", {"KEY": NEIS, "Type": "json", "pIndex": 1, "pSize": 5, "ATPT_OFCDC_SC_CODE": "B10", "ADMST_ZONE_NM": g})
    try: print(" ", g, d["acaInsTiInfo"][0]["head"][0]["list_total_count"])
    except Exception: print(" ", g, str(d)[:120])
print("== 2. 나이스 학교 (B10) 주소에 구 이름")
d = get("https://open.neis.go.kr/hub/schoolInfo", {"KEY": NEIS, "Type": "json", "pIndex": 1, "pSize": 1000, "ATPT_OFCDC_SC_CODE": "B10"})
rows = (d.get("schoolInfo") or [{}, {}])[1].get("row", []) if isinstance(d, dict) else []
for g in GUS: print(" ", g, sum(1 for r in rows if g in (r.get("ORG_RDNMA") or "")), "/ 첫 1000곳 중")
print("== 3. 정보나루 서울(11) 세부지역 코드 찾기")
for c in range(11010, 11260, 10):
    d = get("https://data4library.kr/api/libSrch", {"authKey": LIB, "format": "json", "region": 11, "dtl_region": c, "pageNo": 1, "pageSize": 3})
    libs = [x.get("lib", x) for x in (d.get("response", {}).get("libs") or [])] if isinstance(d, dict) else []
    n = d.get("response", {}).get("numFound") if isinstance(d, dict) else None
    addr = libs[0].get("address", "")[:20] if libs else ""
    m = re.search(r"\S+구", addr or "")
    if n: print(" ", c, n, m.group(0) if m else addr)
print("== 4. 유치원 알리미 서울(11)")
for g, c in GUS.items():
    t = get("https://e-childschoolinfo.moe.go.kr/api/notice/basicInfo2.do", {"key": KIN, "sidoCode": 11, "sggCode": c, "pageCnt": 1000, "currentPage": 1})
    print(" ", g, len(t.get("kinderInfo") or []) if isinstance(t, dict) else str(t)[:100])
print("== 5. KOPIS 서울(11) 아동공연")
for g, c in GUS.items():
    t = get("https://www.kopis.or.kr/openApi/restful/pblprfr", {"service": KOP, "stdate": "20261101", "eddate": "20261231", "cpage": 1, "rows": 100, "signgucode": "11", "signgucodesub": c[:4], "kidstate": "Y"}, raw=True)
    print(" ", g, c[:4], (t.count("<db>") if isinstance(t, str) else t))
print("== 6. 에어코리아 서울 측정소")
d = get("http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty", {"serviceKey": WK, "returnType": "json", "numOfRows": 200, "pageNo": 1, "sidoName": "서울", "ver": "1.3"})
try: print(" ", [i["stationName"] for i in d["response"]["body"]["items"]])
except Exception: print(" ", str(d)[:200])
print("== 7. 지자체 복지 서울특별시 + 구")
for g in GUS:
    t = get("https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfarelist", {"serviceKey": WK, "pageNo": 1, "numOfRows": 5, "ctpvNm": "서울특별시", "sggNm": g}, raw=True)
    m = re.search(r"<totalCount>(\d+)", t if isinstance(t, str) else "")
    print(" ", g, m.group(1) if m else str(t)[:120])
print("== 8. 국립중앙의료원 병의원 서울특별시 + 구")
for g in GUS:
    t = get("https://apis.data.go.kr/B552657/HsptlAsembySearchService/getHsptlMdcncListInfoInqire", {"serviceKey": WK, "Q0": "서울특별시", "Q1": g, "pageNo": 1, "numOfRows": 3}, raw=True)
    m = re.search(r"<totalCount>(\d+)", t if isinstance(t, str) else "")
    print(" ", g, m.group(1) if m else str(t)[:120])
