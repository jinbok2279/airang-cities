"""아이와 함께 갈 만한 성남 행사 수집기

1) 공연예술통합전산망(KOPIS) 경기도 아동공연 중 성남 공연장 (성남아트센터·성남아트리움·성남시민회관 등)  → city
2) 한국관광공사 국문 관광정보: 성남에서 열리는 축제·행사                                             → city
3) (보조) 문화체육관광부 문화예술공연(통합) API 의 성남 가족 행사 (CULTURE_KEY)                         → city
결과는 output/events.json 으로 저장한다.

성남시도서관(snlib.go.kr)은 robots.txt로 전체 수집을 막아 두었고, 성남문화재단(snart.or.kr)은
웹 방화벽이 서버 접속을 막아 읽지 않는다. (2026-10-15 확인) → 체험·교육(lib)은 아직 비어 있음.
"""

import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

from htmltree import Tree

KST = timezone(timedelta(hours=9))
SWCF = "https://www.swcf.or.kr/"
UA = {"User-Agent": "Mozilla/5.0 (seongnam-edu-collector; +https://seongnam.songgollab.co.kr)"}
CULTURE_API = "https://api.kcisa.kr/openapi/CNV_060/request"  # 문화체육관광부_문화예술공연(통합)
CULTURE_KEY = os.environ.get("CULTURE_KEY", "").strip()
HORIZON = 60  # 앞으로 며칠 안에 시작하는 행사까지

from city import C, AREA, PLACES as SUWON, NOT_PLACES as NOT_SUWON
CN = AREA[:-1]   # 예: 성남
KID_WORDS = re.compile(r"가족|어린이|아이|키즈|kids|유아|아동|동화|인형|마술|매직|체험|그림책|놀이|과학|축제|페스티벌|야시장|버블|뮤지컬|"
                       r"캐릭터|만들기|숲|생태|방학|꼬마|공주|동물|공룡|로봇|야간개장|야행|미디어아트|자전거|마켓|놀이터", re.I)
NOT_KID = re.compile(r"19세|청소년\s*관람\s*불가|성인\s*대상|성인만|어르신|시니어|트로트|스탠드업|stand-up|웰니스|미식|와인|술|막걸리|"
                     r"취업|창업|직장인|강사\s*양성|자격증", re.I)
KID_TARGET = re.compile(r"유아|어린이|아동|초등|가족|부모|자녀|아이|키즈|[1-9]\s*세|\d{4}년생|1\s*학년|전\s*연령|누구나|전체")


def get(url, params=None, tries=3, timeout=40):
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(full, headers=UA)
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return res.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  다시 시도 {i + 1}/{tries}: {e}")
            time.sleep(4)
    raise RuntimeError("접속 실패: " + full.split("?")[0])  # 주소 뒤 키는 기록에 남기지 않음


def sp(s):
    return " ".join((s or "").replace("\xa0", " ").split())


def dates(s):
    return [f"{y}-{m}-{d}" for y, m, d in re.findall(r"(\d{4})[.\-](\d{2})[.\-](\d{2})", s or "")]


def months(today):
    """이번 달과 다음 두 달 (60일 안에 시작하는 행사를 다 보기 위해)"""
    out, y, m = [], today.year, today.month
    for _ in range(3):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def swcf_list(page_id, today):
    """수원문화재단 목록(행사 29, 교육 30)을 달별로 읽어 행 목록을 돌려준다."""
    rows, seen = [], set()
    for y, m in months(today):
        try:
            t = Tree(); t.feed(get(SWCF, {"p": page_id, "curYear": y, "curMonth": m}))
        except Exception as e:
            print(f"  {page_id} {y}-{m} 목록 실패:", e)
            continue
        tables = [x for x in t.root.find_all("table") if "b_list" in x.cls()]
        # 열 이름은 표 머리(th)에서 읽는다 (data-cell-header1 은 브라우저 스크립트가 나중에 붙여서 원본 HTML에는 없음)
        heads = [sp(th.all_text()) for th in (tables[0].find_all("th") if tables else [])]
        for tr in (tables[0].find_all("tr") if tables else []):
            tds = tr.find_all("td")
            a = tr.find("a")
            href = (a.attrs.get("href") or "") if a else ""
            mm = re.search(r"idx=(\d+)", href)
            if not tds or not mm or mm.group(1) in seen:
                continue
            seen.add(mm.group(1))
            cell = {(sp(td.attrs.get("data-cell-header1")) or (heads[i] if i < len(heads) else str(i))): sp(td.all_text())
                    for i, td in enumerate(tds)}
            title = sp(a.all_text())
            title = re.sub(r"\s*(재단행사|재단 교육)\s*$", "", title).strip()
            link = re.sub(r"[?&]page=\d+", "", SWCF.rstrip("/") + "/" + href.lstrip("/"))
            rows.append({"idx": mm.group(1), "title": title, "cell": cell, "link": link})
        time.sleep(0.4)
    return rows


def swcf_detail(link):
    """상세 표(분류·기간·시간·장소·관람료·대상 등)와 본문 글"""
    t = Tree(); t.feed(get(link, tries=2))
    info = {}
    for tb in t.root.find_all("table"):
        if "list2" not in tb.cls():
            continue
        for tr in tb.find_all("tr"):
            th, td = tr.find("th"), tr.find("td")
            if th and td:
                info[sp(th.all_text())] = sp(td.all_text())
        break
    body = sp(t.root.all_text())
    book = ""
    for a in t.root.find_all("a"):
        h = a.attrs.get("href") or ""
        if re.search(r"신청|예약|예매", a.all_text()) and h.startswith("http") and "swcf.or.kr" not in h:
            book = h
            break
    return info, body, book


def grade_of(body):
    m = re.search(r"(관람\s*등급|관람\s*연령|참여\s*대상|교육\s*대상|대상)\s*[:：]\s*([^.。\n]{1,90})", body)
    if not m:
        return ""
    g = re.split(r"\s+\S{1,6}\s*[:：]", sp(m.group(2)))[0]  # 다음 항목('관람료 :' 등) 앞에서 자르기
    return g.strip(" ,")


def min_age(text):
    """'8세 이상', '초등학교 1학년', '2019년생' 같은 표현에서 최소 나이(만) 추정. 모르면 None"""
    m = re.search(r"(\d{1,2})\s*세\s*이상", text)
    if m:
        return int(m.group(1))
    if re.search(r"유아|미취학|\d+\s*개월", text):
        return 3
    if re.search(r"초등|어린이|아동", text):
        return 7
    if re.search(r"중학|청소년|13세", text):
        return 13
    if re.search(r"고등|성인|대학생", text):
        return 17
    return None


def foundation_events(today):
    t0, t1 = today.isoformat(), (today + timedelta(days=HORIZON)).isoformat()
    out = []
    for r in swcf_list(29, today):
        ds = dates(r["cell"].get("행사기간", ""))
        if not ds:
            continue
        start, end = ds[0], ds[-1]
        if end < t0 or start > t1 or NOT_KID.search(r["title"]):
            continue
        kind = r["cell"].get("분류", "")
        try:
            info, body, book = swcf_detail(r["link"])
        except Exception as e:
            print("  상세 실패:", r["idx"], e)
            info, body, book = {}, "", ""
        grade = grade_of(body)
        age = min_age(grade)
        if age is not None and age >= 13:
            continue
        kid = bool(KID_WORDS.search(r["title"])) or (age is not None and age <= 10) or kind in ("축제",)
        if not kid:
            continue
        price = info.get("관람료") or info.get("이용료") or ""
        out.append({"id": "S" + r["idx"], "title": r["title"], "start": start, "end": end,
                    "place": r["cell"].get("장소", "") or info.get("장소", ""), "time": info.get("시간", "")[:40],
                    "grade": grade[:30], "price": price[:40], "free": bool(re.search(r"무료", price)) or (not price and kind == "축제"),
                    "kind": kind, "src": "swcf", "link": r["link"], "book": book})
        time.sleep(0.3)
    print(f"  수원문화재단 행사: 아이와 갈 만한 것 {len(out)}건")
    return out


def foundation_programs(today):
    t0 = today.isoformat()
    out = []
    for r in swcf_list(30, today):
        state = r["cell"].get("상태", "")
        if re.search(r"마감|종료", state):
            continue
        ds = dates(r["cell"].get("교육기간", ""))
        if ds and ds[-1] < t0:
            continue
        if NOT_KID.search(r["title"]) or re.search(r"성인|청소년", r["cell"].get("분류", "")):
            continue
        try:
            info, body, book = swcf_detail(r["link"])
        except Exception as e:
            print("  상세 실패:", r["idx"], e)
            continue
        target = grade_of(body)
        if not KID_TARGET.search(target + " " + r["title"] + " " + r["cell"].get("분류", "")):
            continue
        age = min_age(target)
        if age is not None and age >= 13 and not re.search(r"가족|부모|초등", target):
            continue
        ads = dates(info.get("접수기간", ""))
        status = "접수중" if "접수중" in state else "접수전" if re.search(r"예정|대기|접수전", state) else "접수중"
        if ads and ads[-1] < t0:
            continue
        out.append({"id": "E" + r["idx"], "title": r["title"], "lib": r["cell"].get("장소", "") or info.get("교육장소", ""),
                    "target": target[:40], "place": info.get("교육장소", ""),
                    "start": ds[0] if ds else "", "end": ds[-1] if ds else "", "period": r["cell"].get("교육기간", ""),
                    "applyStart": ads[0] if ads else "", "applyEnd": ads[-1] if ads else "", "apply": info.get("접수기간", ""),
                    "count": "", "status": status, "price": (info.get("이용료") or "")[:30],
                    "free": bool(re.search(r"무료", info.get("이용료") or "")), "src": "swcf",
                    "link": book or r["link"]})
        time.sleep(0.3)
    print(f"  수원문화재단 교육: 어린이·가족 대상 {len(out)}건")
    return out


GGAC = "https://www.ggac.or.kr"
GGAC_LIST = GGAC + "/ajax/ggac/schedule/template.do"
GGAC_VIEW = GGAC + "/ggac/M0000155/show/view.do"
# 경기아트센터(수원 인계동) 안의 공연장 이름. '국악당(용인)'처럼 다른 지역 공연장은 뺀다.
GGAC_HALL = re.compile(r"^(대극장|소극장|야외극장|야외공연장|전시실|갤러리|경기아트센터|.*수원)")


def post(url, form, tries=3, timeout=40):
    body = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(url, data=body, headers=dict(UA, **{"Content-Type": "application/x-www-form-urlencoded"}))
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return res.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  다시 시도 {i + 1}/{tries}: {e}")
            time.sleep(4)
    raise RuntimeError("접속 실패: " + url)


def ggac_events(today):
    """경기아트센터 공연·전시 일정 중 수원 공연장에서 열리는 가족·어린이 공연"""
    import calendar
    t0, t1 = today.isoformat(), (today + timedelta(days=HORIZON)).isoformat()
    found, seen = [], set()
    for y, m in months(today):
        last = calendar.monthrange(y, m)[1]
        for page in range(1, 11):
            form = {"searchType": "", "searchLocPerform": "CD001044", "cBtn": "", "year": y, "month": m,
                    "searchSdate": f"{y}-{m:02d}-01", "searchEdate": f"{y}-{m:02d}-{last}", "pageIndex": page,
                    "searchTicker": "", "searchKeyword": ""}
            try:
                t = Tree(); t.feed(post(GGAC_LIST, form))
            except Exception as e:
                print(f"  경기아트센터 {y}-{m} {page}쪽 실패:", e); break
            items = [x for x in t.root.find_all("div") if "item" in x.cls()]
            new = 0
            for it in items:
                txt = next((p for p in it.find_all("p") if "txt" in p.cls()), None)
                a = txt.find("a") if txt else None
                mm = re.search(r"idx=(\w+)", (a.attrs.get("href") or "") if a else "")
                if not mm or mm.group(1) in seen:
                    continue
                seen.add(mm.group(1)); new += 1
                st, dt, pl = a.find("strong"), a.find("span", "date"), a.find("span", "place")
                kind = it.find("i")
                found.append({"idx": mm.group(1), "title": sp(st.all_text() if st else ""), "dates": dates(dt.all_text() if dt else ""),
                              "place": sp(pl.all_text() if pl else ""), "kind": sp(kind.all_text() if kind else "")})
            if not items or not new:
                break
            time.sleep(0.4)
    out = []
    for f in found:
        if not f["dates"]:
            continue
        start, end = f["dates"][0], f["dates"][-1]
        if end < t0 or start > t1 or not GGAC_HALL.search(f["place"]) or NOT_SUWON.search(f["place"]) or NOT_KID.search(f["title"]):
            continue
        link = GGAC_VIEW + "?idx=" + f["idx"]
        info = {}
        try:
            t = Tree(); t.feed(get(link, tries=2))
            for dl in t.root.find_all("dl"):
                dt_, dd = dl.find("dt"), dl.find("dd")
                if dt_ and dd:
                    info[sp(dt_.all_text())] = sp(dd.all_text())
        except Exception as e:
            print("  경기아트센터 상세 실패:", f["idx"], e)
        grade = info.get("관람연령", "")
        age = min_age(grade)
        # 일반 음악회(만 7세 이상 등)는 빼고, 제목이 가족·어린이용이거나 영유아도 볼 수 있는 공연만
        if not (KID_WORDS.search(f["title"]) or (age is not None and age <= 4)):
            continue
        if age is not None and age >= 13:
            continue
        price = info.get("티켓가격", "")
        out.append({"id": "G" + f["idx"], "title": f["title"], "start": start, "end": end,
                    "place": "경기아트센터 " + f["place"] if not f["place"].startswith("경기아트센터") else f["place"],
                    "time": "", "grade": grade[:30], "price": price[:40], "free": bool(re.search(r"무료", price)),
                    "kind": f["kind"], "src": "ggac", "link": link})
        time.sleep(0.3)
    print(f"  경기아트센터: 수원 가족·어린이 공연 {len(out)}건")
    return out


KOPIS_KEY = os.environ.get("KOPIS_KEY", "").strip()
KOPIS_API = "https://www.kopis.or.kr/openApi/restful/pblprfr"  # https 우선 (키 보호)
KOPIS_API_HTTP = "http://kopis.or.kr/openApi/restful/pblprfr"
KOPIS_VIEW = "https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?menuId=MNU_00020&mt20Id="
TOUR_KEY = os.environ.get("TOUR_KEY", "").strip()
TOUR_API = "https://apis.data.go.kr/B551011/KorService2/searchFestival2"


def xml_items(raw, tag):
    root = ET.fromstring(raw.encode("utf-8"))
    return root, [{c.tag: sp(c.text) for c in el} for el in root.iter(tag)]


def kopis_events(today):
    """KOPIS 공연예술통합전산망: 경기도 아동공연(kidstate=Y) 중 성남 공연장"""
    if not KOPIS_KEY:
        print("  KOPIS_KEY 없음: 공연예술통합전산망 건너뜀")
        return []
    t0, t1 = today.strftime("%Y%m%d"), (today + timedelta(days=HORIZON)).strftime("%Y%m%d")
    rows, out, seen = [], [], set()
    # 성남시 코드(4113)로 먼저 받고, 비어 있으면 경기도 전체에서 공연장 이름으로 거른다
    for sub in (C["kopis"], ""):
        got = []
        for page in range(1, 11):
            q = {"service": KOPIS_KEY, "stdate": t0, "eddate": t1, "cpage": page, "rows": 100,
                 "signgucode": "41", "kidstate": "Y"}
            if sub:
                q["signgucodesub"] = sub
            try:
                try:
                    raw = get(KOPIS_API, q, tries=2, timeout=40)
                except Exception:
                    raw = get(KOPIS_API_HTTP, q, tries=1, timeout=40)
                root, items = xml_items(raw, "db")
            except Exception as e:
                print("  KOPIS 실패:", str(e).replace(KOPIS_KEY, "***")[:150]); return []
            if page == 1 and not items:
                msg = sp(root.findtext(".//returncode") or root.findtext(".//errmsg") or "")
                if msg:
                    print("  KOPIS 응답:", msg[:100])
            got += items
            if len(items) < 100:
                break
            time.sleep(0.3)
        print(f"  KOPIS {CN if sub else '경기 전체'} 아동공연 {len(got)}건")
        rows = got
        if got:
            break
    for d in rows:
        pid = d.get("mt20id", "")
        place = d.get("fcltynm", "")
        if not pid or pid in seen:
            continue
        if not SUWON.search(place + " " + d.get("area", "")) or NOT_SUWON.search(place):
            continue
        seen.add(pid)
        ds = [x.replace(".", "-") for x in (d.get("prfpdfrom", ""), d.get("prfpdto", "")) if x]
        if not ds:
            continue
        poster = d.get("poster", "")
        out.append({"id": "K" + pid, "title": d.get("prfnm", ""), "start": ds[0], "end": ds[-1], "place": place,
                    "time": "", "grade": "아동공연", "price": "", "free": False, "kind": d.get("genrenm", ""),
                    "src": "kopis", "link": KOPIS_VIEW + pid,
                    "img": poster.replace("http://", "https://") if poster else ""})
    print(f"  KOPIS {CN} 아동공연 {len(out)}건")
    return out


def tour_festivals(today):
    """한국관광공사 국문 관광정보: 성남에서 열리는 축제·행사"""
    if not TOUR_KEY:
        print("  TOUR_KEY 없음: 관광공사 축제 건너뜀")
        return []
    t0, t1 = today.strftime("%Y%m%d"), (today + timedelta(days=HORIZON)).strftime("%Y%m%d")
    key = TOUR_KEY if "%" in TOUR_KEY else urllib.parse.quote(TOUR_KEY, safe="")
    out, items = [], []
    for page in range(1, 6):
        url = (f"{TOUR_API}?serviceKey={key}&MobileOS=ETC&MobileApp=Airang&_type=json&arrange=A"
               f"&eventStartDate={(today - timedelta(days=90)).strftime('%Y%m%d')}&areaCode=31&numOfRows=100&pageNo={page}")
        try:
            data = json.loads(get(url, tries=2, timeout=40))
        except Exception as e:
            print("  관광공사 실패:", str(e).replace(TOUR_KEY, "***")[:150]); break
        body = (data.get("response") or {}).get("body") or {}
        got = ((body.get("items") or {}) or {}).get("item") or []
        if isinstance(got, dict):
            got = [got]
        if page == 1 and not got:
            print("  관광공사 응답:", str(data)[:200].replace(TOUR_KEY, "***"))
        items += got
        if len(got) < 100:
            break
    for it in items:
        addr = sp(it.get("addr1"))
        if CN not in addr:
            continue
        s, e = str(it.get("eventstartdate") or ""), str(it.get("eventenddate") or "")
        if not s or (e or s) < t0 or s > t1:
            continue
        title = sp(it.get("title"))
        out.append({"id": "T" + str(it.get("contentid")), "title": title,
                    "start": f"{s[:4]}-{s[4:6]}-{s[6:8]}", "end": f"{(e or s)[:4]}-{(e or s)[4:6]}-{(e or s)[6:8]}",
                    "place": addr.replace("경기도 ", ""), "time": "", "grade": "", "price": "", "free": False,
                    "kind": "축제", "src": "tour", "img": (it.get("firstimage") or "").replace("http://", "https://"),
                    "link": "https://search.naver.com/search.naver?query=" + urllib.parse.quote(title)})
    print(f"  관광공사 {CN} 축제·행사 {len(out)}건")
    return out


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&quot;", '"')
    return " ".join(s.split())


def is_suwon(title, site, contact, desc):
    where = " ".join([site, contact])
    if SUWON.search(where) and not (NOT_SUWON.search(where) and CN not in where):
        return True
    if not site and (CN in title or CN in desc[:300]):
        return True
    return bool(re.search(CN, title)) and not NOT_SUWON.search(site)


def culture_events(today):
    """보조: 문화포털 공연 API (해외 서버 접속을 막는 경우가 있어 실패하면 바로 건너뜀)"""
    if not CULTURE_KEY:
        return []
    horizon, t0 = (today + timedelta(days=HORIZON)).strftime("%Y%m%d"), today.strftime("%Y%m%d")
    key = CULTURE_KEY if "%" in CULTURE_KEY else urllib.parse.quote(CULTURE_KEY, safe="")
    out, seen, rows = [], set(), 1000
    for page in range(1, 41):
        url = f"{CULTURE_API}?serviceKey={key}&numOfRows={rows}&pageNo={page}&dtype=&title="
        try:
            raw = get(url, tries=1 if page == 1 else 2, timeout=60)
            root = ET.fromstring(raw.encode("utf-8"))
        except Exception as e:
            print("  문화포털 건너뜀:", str(e).replace(CULTURE_KEY, "***")[:120]); break
        items = root.findall(".//item")
        if not items:
            break
        for it in items:
            g = lambda k: " ".join((it.findtext(k) or "").split())
            ds = re.findall(r"(\d{8})", g("period"))
            if not ds:
                continue
            start, end = ds[0], ds[-1]
            if end < t0 or start > horizon:
                continue
            title, site, desc, contact = g("title"), g("eventSite"), strip_html(it.findtext("description")), g("contactPoint")
            if not is_suwon(title, site, contact, desc):
                continue
            hay = title + " " + desc[:600] + " " + g("charge")
            kid = bool(KID_WORDS.search(title)) or bool(re.search(r"전체\s*관람|어린이|가족|아동|유아|\d+\s*개월|초등", hay))
            if not kid or NOT_KID.search(title) or re.search(r"19세 이상|청소년\s*관람\s*불가", hay) or (title, start) in seen:
                continue
            seen.add((title, start))
            charge = g("charge")
            out.append({"id": "C" + hashlib.md5((title + start).encode()).hexdigest()[:10], "title": title,
                        "start": f"{start[:4]}-{start[4:6]}-{start[6:]}", "end": f"{end[:4]}-{end[4:6]}-{end[6:]}",
                        "place": site, "time": g("eventPeriod")[:60], "grade": "", "price": charge[:40],
                        "free": bool(re.search(r"무료", charge)), "src": "culture",
                        "link": g("url") or "https://search.naver.com/search.naver?query=" + urllib.parse.quote(title)})
        if len(items) < rows:
            break
    print(f"  문화포털 {CN} 가족 행사 {len(out)}건")
    return out


def main():
    today = datetime.now(KST).date()
    city, lib = [], []
    def norm(s):  # 같은 공연이 출처마다 조금 다르게 적혀도 하나로 보기
        s = re.sub(r"\[[^\]]*\]|\([^)]*\)|-\s*" + CN + "$|" + CN + "|가족|뮤지컬|어린이|연극|공연", "", s)
        return re.sub(r"\W", "", s)[:10]
    for name, fn in (("KOPIS", kopis_events), ("관광공사", tour_festivals)):
        try:
            city += [e for e in fn(today) if all(norm(e["title"]) != norm(c["title"]) for c in city)]
        except Exception as e:
            print(f"{name} 실패:", e)
    try:
        city += [e for e in culture_events(today) if all(norm(e["title"]) != norm(c["title"]) for c in city)]
    except Exception as e:
        print("문화포털 실패:", e)
    old = {}
    if os.path.exists("output/events.json"):
        try:
            old = json.load(open("output/events.json", encoding="utf-8"))
        except Exception:
            old = {}
    if not city and old.get("city"):
        city = [e for e in old["city"] if e.get("end", "") >= today.isoformat()]
    if not lib and old.get("lib"):
        lib = [e for e in old["lib"] if (e.get("end") or "9") >= today.isoformat()]
    city.sort(key=lambda e: (max(e["start"], today.isoformat()), e["title"]))
    lib.sort(key=lambda e: (e["status"] != "접수중", e.get("applyEnd") or "9", e["start"]))
    os.makedirs("output", exist_ok=True)
    result = {"updated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
              "source": "공연예술통합전산망·한국관광공사·문화포털", "city": city, "lib": lib}
    with open("output/events.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"공연·축제 {len(city)}건, 체험·교육 {len(lib)}건 저장")
    for e in city[:8]:
        print("  [행사]", e["start"], e["title"], "|", e["place"], "|", e["grade"], e["price"])
    for e in lib[:8]:
        print("  [교육]", e["status"], e["title"], "|", e["target"], e["applyEnd"])


if __name__ == "__main__":
    main()
