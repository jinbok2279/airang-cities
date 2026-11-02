"""도시 공공도서관 목록 수집기 (도서관 정보나루 정보공개 도서관 조회 API)

시 도서관 열람실 실시간 좌석을 공개 API로 내놓지 않아서, 대신
도서관별 주소·전화·운영시간·휴관일·장서 수를 output/libs.json 으로 저장한다. (LIB_KEY 필요)
앱의 '도서관' 탭이 이 파일을 읽는다.
"""

import json
import urllib.parse
import urllib.request
import os
import re
from datetime import datetime, timedelta, timezone

import lib4
from city import C, AREA, gu_of, in_area, SIDO

KST = timezone(timedelta(hours=9))
SKIP = re.compile(r"작은도서관|교도소|대학|병원|사단|부대|법원|교회|성당")  # 일반 가족이 이용하기 어려운 곳


def norm_lib(n):
    return re.sub(r"\W|구립|시립|군립|도립|인천광역시|서울특별시|경기도|교육청|" + re.escape(AREA[:-1]), "", n or "")


def std_libs(known):
    key = urllib.parse.unquote(os.environ.get("WEATHER_KEY", "").strip())
    if not key:
        return []
    rows = []
    for page in range(1, 6):
        q = urllib.parse.urlencode({"serviceKey": key, "type": "json", "pageNo": page, "numOfRows": 1000, "ctprvnNm": SIDO["full"]})
        with urllib.request.urlopen(urllib.request.Request("http://api.data.go.kr/openapi/tn_pubr_public_lbrry_api?" + q, headers={"User-Agent": "airang"}), timeout=90) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        it = d["body"]["items"]
        it = it.get("item", []) if isinstance(it, dict) else it
        rows += it
        if len(it) < 1000:
            break
    hm = lambda a, b: f"{a}~{b}" if a and b and a != "00:00" else ""
    out = []
    for r in rows:
        if r.get("lbrrySe") not in ("공공도서관", "어린이도서관"):
            continue
        addr = r.get("rdnmadr") or r.get("lnmadr") or ""
        if not in_area(addr):
            continue
        name = " ".join((r.get("lbrryNm") or "").split())
        k = norm_lib(name)
        if not name or SKIP.search(name) or any(k == x or (min(len(k), len(x)) >= 4 and (k in x or x in k)) for x in known):   # '갈산도서관' = '부평구립갈산도서관'
            continue
        known.add(k)
        wk, sat = hm(r.get("weekdayOperOpenHhmm"), r.get("weekdayOperColseHhmm")), hm(r.get("satOperOperOpenHhmm"), r.get("satOperCloseHhmm"))
        home = (r.get("homepageUrl") or "").strip()
        out.append({"name": name, "gu": (lambda g: "" if g == "기타" else g)(gu_of(addr)), "status": "none", "message": "", "rooms": [], "link": "",
                    "home": home if home.startswith("http") else ("https://" + home if home else ""), "code": "",
                    "addr": addr, "tel": (r.get("phoneNumber") or "").strip(),
                    "hours": ", ".join(x for x in (f"평일 {wk}" if wk else "", f"토요일 {sat}" if sat else "") if x),
                    "closed": (r.get("closeDay") or "").replace("+", ", "), "books": int(re.sub(r"\D", "", str(r.get("bookCo") or "")) or 0),
                    "lat": r.get("latitude") or "", "lng": r.get("longitude") or ""})
    return out


def main():
    if not lib4.KEY:
        raise SystemExit("LIB_KEY가 없습니다. data4library.kr 에서 인증키를 받아 저장소 Secrets에 LIB_KEY로 넣어 주세요.")
    libs, seen = [], set()
    for gu, code in lib4.GU.items():
        resp = lib4.call("libSrch", region=lib4.REGION, dtl_region=code, pageNo=1, pageSize=200)
        rows = lib4.items(resp, "libs", "lib")
        print(f"{gu}: 도서관 {len(rows)}곳")
        for r in rows:
            name = " ".join(str(r.get("libName") or "").split())
            if not name or name in seen or SKIP.search(name):
                continue
            seen.add(name)
            home = (r.get("homepage") or "").strip()
            if home and not home.startswith("http"):
                home = "https://" + home.lstrip("/")
            libs.append({
                "name": name, "gu": (gu if gu in C["gus"] else (lambda g: "" if g == "기타" else g)(gu_of(r.get("address") or ""))), "status": "none", "message": "", "rooms": [], "link": "",
                "home": home, "code": str(r.get("libCode") or ""),
                "addr": " ".join(str(r.get("address") or "").split()), "tel": (r.get("tel") or "").strip(),
                "hours": " ".join(str(r.get("operatingTime") or "").split()),
                "closed": " ".join(str(r.get("closed") or "").split()),
                "books": int(re.sub(r"\D", "", str(r.get("BookCount") or "")) or 0),  # "-" 같은 값은 0
                "lat": r.get("latitude") or "", "lng": r.get("longitude") or "",
            })
    # 세부지역 코드로 안 잡히는 도서관 (예: 인천 미추홀구 — 정보나루에 세부지역 코드 없음) → 시도 전체에서 주소로 찾기
    resp = lib4.call("libSrch", region=lib4.REGION, pageNo=1, pageSize=500)
    extra = 0
    for r in lib4.items(resp, "libs", "lib"):
        name = " ".join(str(r.get("libName") or "").split())
        if not name or name in seen or SKIP.search(name) or not in_area(r.get("address") or ""):
            continue
        seen.add(name); extra += 1
        home = (r.get("homepage") or "").strip()
        if home and not home.startswith("http"):
            home = "https://" + home.lstrip("/")
        libs.append({"name": name, "gu": (lambda g: "" if g == "기타" else g)(gu_of(r.get("address") or "")), "status": "none", "message": "", "rooms": [], "link": "",
                     "home": home, "code": str(r.get("libCode") or ""), "addr": " ".join(str(r.get("address") or "").split()), "tel": (r.get("tel") or "").strip(),
                     "hours": " ".join(str(r.get("operatingTime") or "").split()), "closed": " ".join(str(r.get("closed") or "").split()),
                     "books": int(re.sub(r"\D", "", str(r.get("BookCount") or "")) or 0), "lat": r.get("latitude") or "", "lng": r.get("longitude") or ""})
    if extra:
        print(f"  주소로 더 찾은 도서관 {extra}곳")
    # 공공데이터포털 전국도서관표준데이터: 정보나루에 없는 구립·시립 공공·어린이도서관 채우기 (WEATHER_KEY = 공공데이터포털 키)
    try:
        extra = std_libs({norm_lib(n) for n in seen})
        libs += extra
        print(f"  표준데이터로 더한 도서관 {len(extra)}곳")
    except Exception as e:
        print("  표준데이터 건너뜀:", str(e)[:80])
    if not libs:
        raise SystemExit("도서관 목록을 하나도 가져오지 못했습니다")
    order = list(C["gus"]) + [""]
    libs.sort(key=lambda l: (order.index(l["gu"]) if l["gu"] in order else 9, l["name"]))
    os.makedirs("output", exist_ok=True)
    result = {"updated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
              "source": "도서관 정보나루 (국립중앙도서관)", "source_url": C.get("lib_home", ""), "libraries": libs}
    with open("output/libs.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"{AREA} 도서관 {len(libs)}곳 저장")
    for l in libs[:5]:
        print(f"  [{l['gu']}] {l['name']} · {l['hours'][:30]} · 휴관 {l['closed'][:30]}")


if __name__ == "__main__":
    main()
