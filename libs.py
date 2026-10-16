"""도시 공공도서관 목록 수집기 (도서관 정보나루 정보공개 도서관 조회 API)

시 도서관 열람실 실시간 좌석을 공개 API로 내놓지 않아서, 대신
도서관별 주소·전화·운영시간·휴관일·장서 수를 output/libs.json 으로 저장한다. (LIB_KEY 필요)
앱의 '도서관' 탭이 이 파일을 읽는다.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone

import lib4
from city import C, AREA, gu_of

KST = timezone(timedelta(hours=9))
SKIP = re.compile(r"작은도서관|교도소|대학|병원|사단|부대|법원|교회|성당")  # 일반 가족이 이용하기 어려운 곳


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
