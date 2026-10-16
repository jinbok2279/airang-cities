"""아이랑 운동교실(성남) 수집기

성남도시개발공사 체육시설 사이트(spo.isdc.co.kr)의 센터별 '프로그램안내' 페이지
(누구나 볼 수 있는 안내 표, 로그인 필요 없음)에서 수영·헬스·요가·필라테스·댄스 강좌의
대상·시간·요일·요금을 읽어 output/sports.json 으로 저장한다.
- robots.txt 없음(제한 없음). 센터마다 페이지 한 장씩, 하루 한 번만 읽는다(요청 사이 2초).
- 실시간 남은 자리는 수강신청 화면(접속 대기열·자동화 차단 적용)에만 있어서 읽지 않는다.
  → 앱에는 "요금·시간 안내"만 보여 주고, 신청은 공사 사이트로 연결한다.
"""

import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
BASE = "https://spo.isdc.co.kr"
UA = "Mozilla/5.0 (seongnam-edu-collector; +https://seongnam.songgollab.co.kr)"
APPLY = BASE + "/courseRegist.do"

CENTERS = [
    {"id": "tan", "name": "탄천종합운동장", "area": "분당구 야탑동", "addr": "성남시 분당구 탄천로 215", "tel": "031-725-7100",
     "apply": APPLY, "tags": ["수영", "헬스", "요가·필라테스"], "hours": "", "closed": "", "web": BASE + "/tan_programGuide.do"},
    {"id": "sns", "name": "성남종합운동장", "area": "중원구 성남동", "addr": "성남시 중원구 제일로 60", "tel": "031-754-3100",
     "apply": APPLY, "tags": ["헬스", "댄스·에어로빅"], "hours": "", "closed": "", "web": BASE + "/sns_programGuide.do"},
    {"id": "pgs", "name": "판교스포츠센터", "area": "분당구 판교동", "addr": "성남시 분당구 판교로228번길 55", "tel": "031-724-4660",
     "apply": APPLY, "tags": ["수영", "헬스"], "hours": "", "closed": "", "web": BASE + "/pgs_programGuide.do"},
    {"id": "spo", "name": "평생스포츠센터", "area": "분당구 정자동", "addr": "성남시 분당구 판교로 546", "tel": "031-781-1073",
     "apply": APPLY, "tags": ["수영", "헬스"], "hours": "", "closed": "", "web": BASE + "/spo_programGuide.do"},
    {"id": "ggp", "name": "금곡공원국민체육센터", "area": "분당구 금곡동", "addr": "성남시 분당구 금곡로 302", "tel": "031-727-9990",
     "apply": APPLY, "tags": ["수영", "헬스"], "hours": "", "closed": "", "web": BASE + "/ggp_programGuide.do"},
]

KID = re.compile(r"초등|어린이|유아|아동|키즈|주니어|생존수영|초\s*\d")
SKIP = re.compile(r"자유\s*수영|자유\s*이용|대관|탁구|배드민턴|농구|골프|테니스|풋살|축구|일일|자유이용|월자유|사물함|주차|셔틀|그래비티|위탁")


def num(v):
    try:
        return int(float(str(v).replace(",", "")))
    except ValueError:
        return 0


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            print("  다시 시도:", url.split("/")[-1], e)
            time.sleep(4)
    return ""


def text(h):
    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    lines = [" ".join(html.unescape(x).split()) for x in h.split("\n")]
    return [x for x in lines if x]


def category(t):
    if re.search(r"수영|아쿠아", t):
        return "수영"
    if re.search(r"요가|필라테스", t):
        return "요가·필라테스"
    if re.search(r"댄스|에어로빅|로빅|줌바|발레|라인|체조|방송", t):
        return "댄스·에어로빅"
    if re.search(r"헬스|근력|피트니스|트레이닝|스피닝|서킷", t, re.I):
        return "헬스"
    return ""


def table_rows(tbl):
    """rowspan을 펼쳐서 [ [칸 글자 줄들] ... ] 으로 돌려준다 (rowspan="2 class=.." 같은 깨진 속성도 처리)"""
    grid, pending = [], {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S):
        cells = re.findall(r"<t([dh])([^>]*)>(.*?)</t[dh]>", tr, re.S)
        row, col = [], 0

        def fill():
            nonlocal col
            while col in pending:
                v, left = pending[col]
                row.append(v)
                if left <= 1:
                    del pending[col]
                else:
                    pending[col] = (v, left - 1)
                col += 1
        for kind, attrs, body in cells:
            fill()
            m = re.search(r'rowspan\s*=\s*"?\s*(\d+)', attrs)
            span = int(m.group(1)) if m else 1
            v = text(body)
            row.append(v)
            if span > 1:
                pending[col] = (v, span - 1)
            col += 1
        fill()
        if row and any(row):
            grid.append(row)
    return grid


WD = "월화수목금토일"


def clean_days(lines):
    """요일 칸에서 '월수금', '화, 목', '월~금' 같은 요일 표기만 남긴다"""
    out = []
    for x in lines:
        if x.startswith(("*", "※")):
            continue
        for mm in re.finditer(r"[월화수목금토일](?:\s*[,~·]?\s*\(?[월화수목금토일]\)?)*", x):
            if re.match(r"[가-힣]", x[mm.end():mm.end() + 1]):
                continue   # '수영', '토요일' 같은 낱말 속 글자는 요일이 아님
            m = re.sub(r"\s+", "", mm.group(0)).replace("~(", "~").strip(",~·()")
            if m and m not in out and not (len(m) == 1 and out):
                out.append(m)
    return " / ".join(out[:2])


def n_days(days):
    d = days.split(" / ")[0]
    m = re.match(r"([월화수목금토일])~([월화수목금토일])", d)
    if m:
        return WD.index(m.group(2)) - WD.index(m.group(1)) + 1
    return len(set(c for c in re.sub(r"\(.\)", "", d) if c in WD))


def short_price(lines, kid, days=""):
    """요금 칸에서 한두 줄만: 어린이 강좌면 어린이 요금 위주"""
    pairs, who = [], ""
    for x in lines:
        if not re.search(r"\d[\d,]*\s*원", x):
            who = x
            continue
        pairs.append((who, x))
    if kid:
        pk = [(w, p) for w, p in pairs if re.search(r"어린이|초등|유아", w + p)]
        if pk:
            pairs = pk
    else:
        pa = [(w, p) for w, p in pairs if not re.search(r"어린이|초등|유아|청소년", w + p)]
        if pa:
            pairs = pa
    n = n_days(days) if days else 0
    pn = [(w, p) for w, p in pairs if re.search(rf"주\s*{n}\s*회", p)] if n else []
    if pn:
        pairs = pn
    out = []
    for w, p in pairs[:2]:
        p = re.sub(r"(어린이|일\s*반|청소년|성\s*인)\s*|\([^)]*\)\s*", "", p).strip()
        out.append(p)
    return " / ".join(out)


def parse_center(c, page):
    i = page.find('id="tabs-1"')
    j = page.find('id="tabs-2"', i + 10)
    part = page[i:j if j > 0 else None] if i >= 0 else page
    progs = []
    for head, tbl in re.findall(r"<h5[^>]*>(.*?)</h5>.*?(<table.*?</table>)", part, re.S):
        title = " ".join(text(head))
        title = re.sub(r"\(.*?\)|강습프로그램", "", title)
        title = " ".join(re.split(r"[/(]", title)[0].split()) or "강좌"
        cat = category(title)
        if not cat or SKIP.search(title):
            continue
        grid = table_rows(tbl)
        if not grid:
            continue
        hdr = [" ".join(x) for x in grid[0]]
        def col(*names):
            return next((n for n, h in enumerate(hdr) for k in names if k in h), None)
        idx = {"대상": col("대상", "프로그램"), "시간": col("시간"), "요일": col("요일"), "이용료": col("이용료", "요금", "비고")}
        if idx["대상"] is None or idx["시간"] is None or idx["이용료"] is None:
            continue
        groups = {}
        for row in grid[1:]:
            def g(k):
                return row[idx[k]] if idx[k] is not None and idx[k] < len(row) else []
            wl = [x for x in g("대상") if not re.search(r"^[※*]|주\s*\d\s*회|^\(?[월화수목금토일,\s~()]+\)?$", x)]
            who = re.sub(r"\((?!초|만|여성|\d).*?\)", "", " ".join(wl[:2])).strip()[:30]
            who = who.replace("일 반", "일반")
            if not who or who == title:
                who = "일반·청소년"
            if not who or SKIP.search(who):
                continue
            days = clean_days(g("요일") or g("대상"))
            times = " ".join(re.findall(r"\d{1,2}:\d{2}\s*~\s*\d{1,2}:\d{2}", " ".join(g("시간"))))
            kid = 1 if KID.search(who) else 0
            price = short_price(g("이용료"), kid, days)
            if not times or not price:
                continue
            groups.setdefault((who, days, price), []).append(times)
        for (who, days, price), ts in groups.items():
            kid = 1 if KID.search(who) else 0
            tl = []
            for t in ts:
                for x in re.findall(r"\d{1,2}:\d{2}\s*~\s*\d{1,2}:\d{2}", t):
                    x = x.replace(" ", "")
                    if x not in tl:
                        tl.append(x)
            note = ""
            days_clean = days
            progs.append({"c": c["id"], "cat": cat, "name": f"{title} · {who}", "who": who + (f" ({note})" if note else ""),
                          "kid": kid, "days": days_clean,
                          "times": ", ".join(tl[:6]) + (f" 외 {len(tl) - 6}개 반" if len(tl) > 6 else ""),
                          "price": price, "cap": 0, "applied": 0, "room": ""})
    return progs


def main():
    now = datetime.now(KST)
    city = os.environ.get("CITY", "성남").strip()
    if city != "성남":
        other_city(city, now)
        return
    programs, status = [], {}
    for c in CENTERS:
        page = get(c["web"])
        got = parse_center(c, page) if page else []
        status[c["id"]] = "ok" if got else ("empty" if page else "fail")
        print(f" {c['name']}: {len(got)}개 (아이 {sum(p['kid'] for p in got)})")
        programs += got
        time.sleep(2)
    for p in programs:
        if not p["kid"]:
            p.pop("kid")
    order = ["수영", "댄스·에어로빅", "요가·필라테스", "헬스", "사우나"]
    programs.sort(key=lambda p: (0 if p.get("kid") else 1, order.index(p["cat"]) if p["cat"] in order else 9, p["c"]))
    if not programs:
        print("강좌를 하나도 못 읽었어요. 이전 파일을 그대로 둡니다.")
        return
    out = {"city": "성남", "updated": now.strftime("%Y-%m-%d %H:%M"), "status": status, "live": 0,
           "centers": CENTERS, "programs": programs}
    os.makedirs("output", exist_ok=True)
    with open("output/sports.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"저장: 강좌 {len(programs)}개 (아이 {sum(1 for p in programs if p.get('kid'))}개)")



# ---------- 다른 도시 ----------
UA2 = "Mozilla/5.0 (airang-collector; +https://songgollab.co.kr)"
GYS = "https://yeyak.gys.or.kr"
BEST = "https://www.best.or.kr"
AUC = "https://www.auc.or.kr"
AUC_APPLY = AUC + "/reservation/program/lesson/list?menuLevel=2&menuNo=354"


def get2(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA2})
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            print("  다시 시도:", url[-60:], e)
            time.sleep(4)
    return ""


def place(name, city):
    """카카오 장소 검색으로 주소·전화 (키 없거나 실패하면 빈 값)"""
    key = os.environ.get("KAKAO_KEY", "").strip()
    out = {"addr": "", "tel": "", "area": ""}
    if not key:
        return out
    q = urllib.parse.urlencode({"query": city + " " + name, "size": 5})
    req = urllib.request.Request("https://dapi.kakao.com/v2/local/search/keyword.json?" + q, headers={"Authorization": "KakaoAK " + key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            docs = json.loads(r.read().decode("utf-8")).get("documents") or []
    except Exception as e:
        print("  장소 검색 실패:", name, e)
        return out
    for d in docs:
        if city in d.get("address_name", ""):
            parts = d["address_name"].split()
            out = {"addr": d.get("road_address_name") or d["address_name"], "tel": d.get("phone", ""),
                   "area": " ".join(x for x in parts[2:4] if re.search(r"[구동읍면]$", x))}
            break
    time.sleep(0.3)
    return out


def is_kid(t):
    return 1 if (KID.search(t) or re.search(r"어린이|유아|청소년|초등|아동|학생", t)) else 0


def tags_of(progs):
    order = ["수영", "헬스", "요가·필라테스", "댄스·에어로빅"]
    have = {p["cat"] for p in progs}
    return [t for t in order if t in have]


def goyang():
    programs, centers, status = [], {}, {}
    for i in range(1, 13):
        code = f"GYS{i:02d}"
        got = 0
        for pg in range(1, 40):
            page = get2(f"{GYS}/fmcs/1?companyCode={code}&page={pg}")
            body = page[page.find("<tbody"):page.find("</tbody>")] if "<tbody" in page else ""
            rows = [r for r in re.findall(r"(?s)<tr>(.*?)</tr>", body) if "<td" in r]
            rows = [re.findall(r"(?s)<td[^>]*>(.*?)</td>", r) for r in rows]
            rows = [r for r in rows if len(r) >= 9]
            if not rows:
                break
            for r in rows:
                center = " ".join(text(r[1]))
                name = " ".join(text(r[2]))
                tm = text(r[3]); days = tm[0] if tm else ""; times = " ".join(tm[1:]).replace(" ~ ", "~")
                period = " ".join(text(r[4])); who = " ".join(text(r[5])); fee = " ".join(text(r[6])); state = " ".join(text(r[8]))
                t = name + " " + who
                cat = category(t)
                if not cat or SKIP.search(name):
                    continue
                m = re.match(r"\d{4}-(\d{2})", period)
                programs.append({"c": code, "cat": cat, "name": name, "who": who, "kid": is_kid(who + " " + name),
                                 "days": days, "times": times, "price": fee + "원" if fee and fee[0].isdigit() else fee,
                                 "state": state, "month": int(m.group(1)) if m else 0})
                centers.setdefault(code, center)
                got += 1
            if f"page={pg + 1}" not in page:
                break
            time.sleep(1)
        status[code] = "ok" if got else "empty"
        if got:
            print(f" 고양 {centers[code]}: {got}개")
        time.sleep(1)
    cs = []
    for code, nm in centers.items():
        pl = place(nm, "고양")
        cs.append({"id": code, "name": nm, "area": pl["area"], "addr": pl["addr"], "tel": pl["tel"], "hours": "", "closed": "",
                   "tags": tags_of([p for p in programs if p["c"] == code]), "web": f"{GYS}/fmcs/1?companyCode={code}", "apply": f"{GYS}/fmcs/1?companyCode={code}"})
    return {"status": status, "live": 0, "centers": cs, "programs": programs,
            "note": "접수 상태는 하루 한 번 새로 받아요. 신청은 고양도시관리공사 통합예약에서 해요."}


def bucheon():
    programs, status = [], {}
    try:
        comps = json.loads(get2(BEST + "/rest/common/company") or "[]")
    except ValueError:
        comps = []
    comps = [c for c in comps if not re.search(r"종합운동장|배드민턴", c.get("comnm", ""))]
    for c in comps:
        got = 0
        for pg in range(1, 10):
            q = urllib.parse.urlencode({"company_code": c["comcd"], "mem_no": "", "search_type": "", "category_cd": "", "category_level": 9,
                                        "class_nm": "", "train_day": "", "adult_gubn": "", "lecturer_nm": "", "page": pg, "page_size": 100})
            try:
                rows = json.loads(get2(BEST + "/rest/lecture/list?" + q) or "[]")
            except ValueError:
                rows = []
            if not isinstance(rows, list) or not rows:
                break
            for d in rows:
                name = (d.get("class_nm") or "").strip()
                t = " ".join([name, d.get("category1") or "", d.get("category2") or "", d.get("target_age_name") or ""])
                cat = category(t)
                if not cat or SKIP.search(name + " " + (d.get("category2") or "")):
                    continue
                cap, appl = num(d.get("capa")), num(d.get("reg_person"))
                programs.append({"c": c["comcd"], "cat": cat, "name": re.sub(r"^추첨-\s*", "", name) + (" (추첨)" if name.startswith("추첨") else ""),
                                 "who": d.get("target_age_name") or "", "kid": is_kid(t), "days": d.get("train_day_nm") or "",
                                 "times": f"{d.get('train_stime', '')}~{d.get('train_etime', '')}", "price": (d.get("course_fee") or "") + "원",
                                 "cap": cap, "applied": appl, "month": 0})
                got += 1
            total = num(rows[0].get("total_count")) if rows else 0
            if pg * 100 >= total:
                break
            time.sleep(1)
        status[c["comcd"]] = "ok" if got else "empty"
        print(f" 부천 {c['comnm']}: {got}개")
        time.sleep(1)
    cs = []
    for c in comps:
        mine = [p for p in programs if p["c"] == c["comcd"]]
        if not mine:
            continue
        pl = place(c["comnm"], "부천")
        cs.append({"id": c["comcd"], "name": c["comnm"], "area": pl["area"], "addr": pl["addr"], "tel": pl["tel"], "hours": "", "closed": "",
                   "tags": tags_of(mine), "web": f"{BEST}/fmcs/271?center={c['comcd']}", "apply": f"{BEST}/fmcs/271?center={c['comcd']}"})
    return {"status": status, "live": 1, "centers": cs, "programs": programs}


def centers_only(city):
    """강좌 목록을 가져올 수 없는 도시: 센터·전화·신청 바로가기만"""
    if city == "안양":
        base = [("안양수영장", f"{AUC}/reservation/contents/view?contentsNo=76&menuLevel=3&menuNo=49", ["수영"]),
                ("호계수영장", f"{AUC}/reservation/contents/view?contentsNo=307&menuLevel=3&menuNo=76", ["수영"]),
                ("호현수영장", f"{AUC}/reservation/contents/view?contentsNo=308&menuLevel=3&menuNo=77", ["수영"])]
        why = "안양도시공사는 강좌 목록을 로그인해야 보여 줘요. 센터 홈페이지에서 강좌와 남은 자리를 확인해 주세요."
        cs = []
        for i, (nm, web, tags) in enumerate(base):
            pl = place(nm, "안양")
            cs.append({"id": f"a{i}", "name": nm, "area": pl["area"], "addr": pl["addr"], "tel": pl["tel"], "hours": "", "closed": "",
                       "tags": tags, "web": web, "apply": AUC_APPLY})
    else:   # 화성: 화성도시공사 체육 사이트는 자동 수집을 막아 두어 홈페이지로 연결만
        cs = [{"id": "h0", "name": "화성도시공사 체육시설", "area": "화성시", "addr": "", "tel": "", "hours": "", "closed": "",
               "tags": ["수영", "헬스", "요가·필라테스"], "web": "https://hssports.hscity.go.kr/", "apply": "https://hssports.hscity.go.kr/"}]
        why = "화성도시공사 체육시설 강좌는 홈페이지에서 직접 확인해 주세요. 강좌 목록은 기관과 협의되면 모아 드릴게요."
    return {"status": {}, "live": 0, "only": 1, "why": why, "centers": cs, "programs": []}


def other_city(city, now):
    fn = {"고양": goyang, "부천": bucheon}.get(city)
    res = fn() if fn else centers_only(city) if city in ("안양", "화성") else None
    if res is None:
        res = {"status": {}, "live": 0, "soon": 1, "centers": [], "programs": []}
    elif fn and not res["programs"]:
        print("강좌를 하나도 못 읽었어요. 이전 파일을 그대로 둡니다.")
        return
    for p in res["programs"]:
        if not p.get("kid"):
            p.pop("kid", None)
    order = ["수영", "댄스·에어로빅", "요가·필라테스", "헬스", "사우나"]
    res["programs"].sort(key=lambda p: (0 if p.get("kid") else 1, order.index(p["cat"]) if p["cat"] in order else 9, p["c"], p.get("times", "")))
    out = {"city": city, "updated": now.strftime("%Y-%m-%d %H:%M"), **res}
    os.makedirs("output", exist_ok=True)
    with open("output/sports.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"저장: {city} 센터 {len(out['centers'])}곳, 강좌 {len(out['programs'])}개 (아이 {sum(1 for p in out['programs'] if p.get('kid'))}개)")

if __name__ == "__main__":
    main()
