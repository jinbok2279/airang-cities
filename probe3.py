"""인천 열기 전 확인 (한 번 쓰고 지움) — 키 값은 찍지 않음"""
import json, os, re, urllib.parse, urllib.request, collections
def get(url, params, raw=False):
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "airang-probe"}), timeout=60) as r:
            t = r.read().decode("utf-8", "replace")
        return t if raw else json.loads(t)
    except Exception as e:
        return {"_err": str(e)[:120]}
NEIS = os.environ["NEIS_KEY"]; LIB = os.environ["LIB_KEY"]; KK = os.environ["KINDER_KEY"]; WK = urllib.parse.unquote(os.environ["WEATHER_KEY"])
NAMES = ["중구", "동구", "제물포구", "영종구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구", "검단구", "강화군", "옹진군"]
print("== 학원 수 (나이스 E10, 행정구역명)")
for z in NAMES:
    d = get("https://open.neis.go.kr/hub/acaInsTiInfo", {"KEY": NEIS, "Type": "json", "pIndex": 1, "pSize": 1, "ATPT_OFCDC_SC_CODE": "E10", "ADMST_ZONE_NM": z})
    try: print(" ", z, d["acaInsTiInfo"][0]["head"][0]["list_total_count"])
    except Exception: print(" ", z, str(d)[:80])
print("== 학교 주소의 구 (나이스 E10)")
c = collections.Counter()
for p in range(1, 4):
    d = get("https://open.neis.go.kr/hub/schoolInfo", {"KEY": NEIS, "Type": "json", "pIndex": p, "pSize": 1000, "ATPT_OFCDC_SC_CODE": "E10"})
    try: rows = d["schoolInfo"][1]["row"]
    except Exception: break
    for r in rows:
        m = re.search(r"인천광역시\s+(\S+[구군])", r.get("ORG_RDNMA") or "")
        c[(m.group(1) if m else "?") + "/" + (r.get("SCHUL_KND_SC_NM") or "")[:2]] += 1
for k, v in sorted(c.items()): print(" ", k, v)
print("== 정보나루 인천(23) 세부지역")
for cc in list(range(23010, 23400, 10)) + [23011, 23012, 23021, 23111, 23112, 23121]:
    d = get("https://data4library.kr/api/libSrch", {"authKey": LIB, "format": "json", "region": 23, "dtl_region": cc, "pageNo": 1, "pageSize": 2})
    r = d.get("response", {}) if isinstance(d, dict) else {}
    libs = [x.get("lib", x) for x in (r.get("libs") or [])]
    if r.get("numFound"): print(" ", cc, r.get("numFound"), (libs[0].get("address", "")[:20] if libs else ""))
print("== 유치원알리미 인천(28)")
for sg in [28110, 28115, 28125, 28140, 28170, 28177, 28185, 28200, 28237, 28245, 28260, 28265, 28270, 28710, 28720]:
    d = get("https://e-childschoolinfo.moe.go.kr/api/notice/basicInfo2.do", {"key": KK, "sidoCode": 28, "sggCode": sg, "pageCnt": 300, "currentPage": 1})
    k = (d.get("kinderInfo") or []) if isinstance(d, dict) else []
    if k: print(" ", sg, len(k), (k[0].get("addr") or "")[:20])
    elif isinstance(d, dict) and d.get("_err"): print(" ", sg, d["_err"][:60])
print("== 에어코리아 인천 측정소")
d = get("http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty", {"serviceKey": WK, "returnType": "json", "numOfRows": 200, "pageNo": 1, "sidoName": "인천", "ver": "1.3"})
try: print(" ", [i["stationName"] for i in d["response"]["body"]["items"]])
except Exception: print(str(d)[:200])
print("== 복지 (지자체 서비스, 시군구 이름)")
for z in NAMES:
    t = get("https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfarelist", {"serviceKey": WK, "pageNo": 1, "numOfRows": 1, "ctpvNm": "인천광역시", "sggNm": z}, raw=True)
    m = re.search(r"<totalCount>(\d+)", t if isinstance(t, str) else ""); print(" ", z, m.group(1) if m else str(t)[:80])
print("== 심평원 병원 (인천 220000) 구 코드")
t = get("https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList", {"serviceKey": WK, "sidoCd": "220000", "numOfRows": 1000, "pageNo": 1}, raw=True)
c = collections.Counter(re.findall(r"<sgguCd>(\d+)</sgguCd><sgguCdNm>([^<]+)</sgguCdNm>", t if isinstance(t, str) else ""))
for k, v in sorted(c.items()): print(" ", k, v)
if not c: print(str(t)[:300])
