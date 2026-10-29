# (2026-10-29 옮겨 옴: 예전 suwon-edu-collector/sports.py 그대로 — 이 도시만 쓰는 수집기)
"""아이랑 운동교실(수원) 수집기

수원도시공사 강좌 예약 사이트(rsv.suwonudc.co.kr)가 누구나 볼 수 있게 보여 주는
강좌 목록(로그인 필요 없음)에서 수영·헬스·요가·필라테스·댄스 강좌와
모집·신청 인원(남은 자리)을 읽어 output/sports.json 으로 저장한다.
- robots.txt 없음(제한 없음). 요청 사이 0.4초 쉬어 서버 부담을 줄인다.
- 강사 이름은 가져오지 않는다.
- 이번 달과 다음 달 반을 함께 본다(다음 달 반이 열려 있으면 그쪽을 먼저 보여 줌).
"""

import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
BASE = "https://rsv.suwonudc.co.kr"
UA = "Mozilla/5.0 (suwon-edu-collector; +https://suwon.songgollab.co.kr)"
APPLY = "https://rsv.suwonudc.co.kr/suwonudc/uat/uia/LoginUsr.do"

CENTERS = [
    {"id": "20010001", "name": "광교웰빙국민체육센터", "area": "영통구 이의동", "addr": "수원시 영통구 웰빙타운로 71", "tel": "031-228-3200",
     "hours": "센터 홈페이지 참고", "closed": "", "tags": ["수영", "헬스", "요가·필라테스", "댄스·에어로빅"],
     "web": "https://www.suwonudc.co.kr/suwonsc3/mainPage.do", "apply": APPLY},
    {"id": "17110001", "name": "서수원칠보체육관", "area": "권선구 금곡동", "addr": "수원시 권선구 서수원로 577", "tel": "031-228-2600",
     "hours": "센터 홈페이지 참고", "closed": "", "tags": ["헬스", "요가·필라테스", "댄스·에어로빅", "탁구", "배드민턴"],
     "web": "https://www.suwonudc.co.kr/suwonsc2/mainPage.do", "apply": APPLY},
    {"id": "17110002", "name": "장안구민회관", "area": "장안구 정자동", "addr": "수원시 장안구 송원로 101", "tel": "031-228-3001",
     "hours": "센터 홈페이지 참고", "closed": "", "tags": ["수영", "헬스"],
     "web": "https://www.suwonudc.co.kr/jacc/mainPage.do", "apply": APPLY},
]

KID = re.compile(r"초등|어린이|유아|아동|키즈|주니어|생존수영")
SKIP = re.compile(r"출근부|강사|대관|탁구|배드민턴|농구|골프|테니스|풋살|축구|문화|체험|사회적약자|다목적체육관|일일|미술|음악|어학|공예|서예|노래|악기|컴퓨터|요리|바둑")
START = time.time()
BUDGET = 15 * 60   # 최대 15분만 돌고, 받은 데까지 저장


def http(url, data=None, ctype=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **({"Content-Type": ctype} if ctype else {})})
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8", errors="replace"))
        except Exception as e:
            print("  다시 시도:", url.split("/")[-1], e)
            time.sleep(3 * (i + 1))
    return None


def codes(agent, code):
    j = http(f"{BASE}/suwonudc/biz/com/GbCodeSelete.do?" + urllib.parse.urlencode({"agentCode": agent, "gbCode1": code}))
    return [(r.get("code"), (r.get("name") or "").strip()) for r in (j or {}).get("rows", [])]


def courses(agent, c1, c2, ym):
    body = json.dumps({"agentcode": agent, "gbcode1": c1, "sYearMon": ym + "01", "gbcode2": c2, "sdate": f"{ym[:4]}-{ym[4:]}-01"}).encode()
    j = http(f"{BASE}/suwonudc/biz/Ncrs/API/sukanglist.do", body, "application/json;charset=UTF-8")
    return j if isinstance(j, list) else []


def category(text):
    if re.search(r"수영|아쿠아", text):
        return "수영"
    if re.search(r"사우나|목욕", text):
        return "사우나"
    if re.search(r"요가|필라테스", text):
        return "요가·필라테스"
    if re.search(r"댄스|에어로빅|로빅|줌바|발레|라인|체조|방송", text):
        return "댄스·에어로빅"
    if re.search(r"헬스|근력|피트니스|PT|트레이닝|스피닝|서킷", text, re.I):
        return "헬스"
    return ""


def num(v):
    try:
        return int(float(str(v).replace(",", "")))
    except ValueError:
        return 0


def main():
    now = datetime.now(KST)
    this_m = now.strftime("%Y%m")
    nxt = (now.replace(day=1) + timedelta(days=32)).strftime("%Y%m")
    months = (nxt, this_m) if now.day >= 20 else (this_m,)   # 다음 달 반은 보통 20일 이후에 열림
    print("조회 달:", months, flush=True)
    programs, status = [], {}
    for c in CENTERS:
        a, got = c["id"], 0
        try:
            for c1, n1 in codes(a, "0000"):
                if SKIP.search(n1):
                    continue
                time.sleep(0.4)
                subs = codes(a, c1)
                print(f" {c['name']} · {n1}: 세부 {len(subs)}개", flush=True)
                for c2, n2 in subs:
                    if SKIP.search(n2) or time.time() - START > BUDGET:
                        continue
                    for ym in months:
                        time.sleep(0.4)
                        for d in courses(a, c1, c2, ym):
                            names = [d.get(k, "") for k in ("skname1", "skname2", "skname3", "skname4")]
                            text = " ".join(names + [n1, n2])
                            cat = category(text)
                            if not cat or SKIP.search(text):
                                continue
                            cap, appl = num(d.get("sktjwcnt")), num(d.get("skcnt"))
                            title = " · ".join(x for x in names[:3] if x)
                            programs.append({
                                "c": a, "cat": cat, "name": title, "who": names[1] or n2,
                                "kid": 1 if KID.search(text) else 0,
                                "days": (d.get("skname6") or "").replace("|", "·"), "times": d.get("skname7") or "",
                                "price": f"{num(d.get('skamt')):,}원" + (f" ({d.get('skname5')})" if d.get("skname5") else ""),
                                "cap": cap, "applied": appl, "month": int(ym[4:]), "ym": ym, "room": d.get("skrname") or ""})
                            got += 1
            status[a] = "ok" if got else "empty"
        except Exception as e:
            print(f" {c['name']} 실패: {e}")
            status[a] = "fail"
        print(f" {c['name']}: {got}개 ({int(time.time() - START)}초)", flush=True)
    # 같은 강좌가 두 달에 다 있으면 다음 달 것만 남김
    seen, uniq = set(), []
    for p in sorted(programs, key=lambda p: p["ym"], reverse=True):
        k = (p["c"], p["name"], p["days"], p["times"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)
    for p in uniq:
        p.pop("ym")
        if not p["kid"]:
            p.pop("kid")
    order = ["수영", "댄스·에어로빅", "요가·필라테스", "헬스", "사우나"]
    uniq.sort(key=lambda p: (0 if p.get("kid") else 1, order.index(p["cat"]) if p["cat"] in order else 9, p["c"], p["times"]))
    if not uniq:
        print("강좌를 하나도 못 읽었어요. 이전 파일을 그대로 둡니다.")
        return
    out = {"city": "수원", "updated": now.strftime("%Y-%m-%d %H:%M"), "status": status, "live": 1, "centers": CENTERS, "programs": uniq}
    os.makedirs("output", exist_ok=True)
    with open("output/sports.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"저장: 강좌 {len(uniq)}개 (아이 {sum(1 for p in uniq if p.get('kid'))}개)")


if __name__ == "__main__":
    main()
