"""도시 공공도서관 인기 도서 수집기 (도서관 정보나루 인기대출도서 API)

1) 초등(8~13세) 인기 도서 - 도시 구별 공공도서관, 최근 1달
2) 청소년(14~19세) 인기 도서 - 도시 구별 공공도서관, 최근 1달
3) 도시 대출 베스트 - 전 연령, 최근 1달
구마다 순위를 받아 대출 건수를 더해 도시 전체 순위를 만든다.
결과는 output/books.json 으로 저장한다. (LIB_KEY 필요)
"""

from city import AREA
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import lib4

KST = timezone(timedelta(hours=9))
TOP = 20
PER_GU = 60  # 구마다 받아 올 순위 수 (합산 후 TOP 만 남김)


def num(v):
    try:
        return int(str(v).replace(",", "").strip())
    except Exception:
        return 0


def clean_title(s):
    s = re.sub(r"^\((만화|그림책|큰글자|전자책)\)\s*", "", (s or "").strip())
    s = re.sub(r"\s+([.,])", r"\1", s)
    return " ".join(s.split())


def series_key(title):
    """같은 시리즈 묶기: 끝의 권 번호('. 15', ' 3', '(2)', '3권')를 떼고 비교"""
    t = re.sub(r"[\s.:,]*(\(\s*\d+\s*\)|\d+\s*권?)\s*$", "", title)
    t = re.sub(r"\s*=.*$", "", t)  # 원제 병기 '= ...' 제거
    return re.sub(r"\W", "", t)


def tidy_author(s):
    s = re.sub(r"(지은이|글|그림|옮긴이|저자|지음|엮음)\s*:\s*", "", s or "")
    s = re.sub(r"\s*;\s*", ", ", s)
    return s.strip(" ,")


def ranked(**filters):
    """도시 구별 순위를 합쳐 대출 건수 순으로 정렬"""
    end = datetime.now(KST).date() - timedelta(days=1)
    start = end - timedelta(days=30)
    merged, ok = {}, 0
    for gu, code in lib4.GU.items():
        try:
            resp = lib4.call("loanItemSrch", startDt=start.isoformat(), endDt=end.isoformat(),
                             region=lib4.REGION, dtl_region=code, pageNo=1, pageSize=PER_GU, **filters)
        except Exception as e:
            print(f"  {gu} 실패: {e}")
            continue
        ok += 1
        docs = lib4.items(resp, "docs", "doc")
        print(f"  {gu}: {len(docs)}권")
        for d in docs:
            isbn = re.sub(r"\D", "", str(d.get("isbn13") or ""))
            title = clean_title(d.get("bookname"))
            key = isbn or re.sub(r"\W", "", title)
            if not key:
                continue
            b = merged.get(key)
            if not b:
                b = merged[key] = {"title": title, "author": tidy_author(d.get("authors")),
                                   "publisher": (d.get("publisher") or "").strip(),
                                   "cover": (d.get("bookImageURL") or "").strip(),
                                   "link": (d.get("bookDtlUrl") or "").strip(), "isbn": isbn, "loans": 0}
            b["loans"] += num(d.get("loan_count"))
        time.sleep(0.4)
    if ok == 0:
        raise RuntimeError("4개 구 모두 실패")
    books, seen = [], {}
    for b in sorted(merged.values(), key=lambda x: -x["loans"]):
        k = series_key(b["title"])
        if k and k in seen:  # 같은 시리즈는 한 줄로
            seen[k]["series"] += 1
            continue
        b = dict(b, rank=len(books) + 1, series=1)
        if b["cover"].startswith("http://"):
            b["cover"] = "https://" + b["cover"][7:]
        seen[k] = b
        books.append(b)
        if len(books) >= TOP:
            break
    return books


def main():
    if not lib4.KEY:
        raise SystemExit("LIB_KEY가 없습니다. data4library.kr 에서 인증키를 받아 저장소 Secrets에 LIB_KEY로 넣어 주세요.")
    plan = [
        ("kids", "초등 인기 도서", AREA + " 공공도서관 · 초등(8~13세) 대출 · 최근 1달", dict(from_age=8, to_age=13)),
        ("teen", "청소년 인기 도서", AREA + " 공공도서관 · 청소년(14~19세) 대출 · 최근 1달", dict(from_age=14, to_age=19)),
        ("suwon", AREA + " 대출 베스트", AREA + " 공공도서관 · 전 연령 · 최근 1달", {}),
    ]
    old = {}
    if os.path.exists("output/books.json"):
        try:
            old = {l["key"]: l for l in json.load(open("output/books.json", encoding="utf-8"))["lists"]}
        except Exception:
            old = {}
    lists = []
    for key, title, desc, f in plan:
        print(f"[{title}]")
        try:
            books = ranked(**f)
        except Exception as e:
            print(f"  실패: {e}")
            books = []
        if not books and key in old:  # 실패하면 지난번 목록 유지
            books = old[key]["books"]
        lists.append({"key": key, "title": title, "desc": desc, "books": books})
        for b in books[:5]:
            print(f"  {b['rank']}. {b['title']} / {b['author']} (대출 {b.get('loans', '-')})")
    if not any(l["books"] for l in lists):
        raise SystemExit("인기 도서를 하나도 가져오지 못했습니다")
    os.makedirs("output", exist_ok=True)
    result = {"updated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"), "source": "도서관 정보나루 (국립중앙도서관)", "lists": lists}
    with open("output/books.json", "w", encoding="utf-8") as fp:
        json.dump(result, fp, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
