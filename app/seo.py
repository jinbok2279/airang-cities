"""검색용 페이지 만들기 — 수집 자료(data/<도시>/*.json)로 네이버·구글이 읽을 수 있는 정적 HTML을 만든다.

  python3 app/seo.py --out out --data data              # 모든 도시
  python3 app/seo.py --out out --data data --city gangnam

만드는 것 (도시 폴더 안, 주소는 <도시>.songgollab.co.kr/guide/...)
  guide/index.html                 도시 안내 (주제별 링크)
  guide/academy/index.html         학원 전체 (과목·동별 개수)
  guide/academy/<과목>.html         과목별 학원 + 교습비(교육청 신고)
  guide/academy/<과목>/<동>.html    동네별 과목 학원 (예: 대치동 수학학원)
  guide/kinder.html                유치원
  guide/library.html               도서관 운영시간·휴관일
  guide/pediatrics.html            소아청소년과 진료 시간
  guide/events.html                아이와 갈 만한 행사
  sitemap.xml, robots.txt
개인정보는 쓰지 않는다 (공공데이터의 기관 이름·주소·전화만).
"""
import argparse, html, json, os, re, statistics
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "cities.json"), encoding="utf-8"))
KST = timezone(timedelta(hours=9))
E = lambda s: html.escape(str(s or ""), quote=True)

SUBJECTS = [  # 주소용 이름, 화면 이름, 학원 이름·강좌 이름에서 찾을 말
    ("math", "수학", r"수학|매스|math|산수|연산"),
    ("english", "영어", r"영어|잉글|english|어학원|리딩|파닉스"),
    ("korean", "국어·논술", r"국어|논술|독서|글쓰기"),
    ("science", "과학", r"과학|사이언스|science|물리|화학|생명"),
    ("art", "미술", r"미술|아트|art|드로잉|그림"),
    ("music", "음악·피아노", r"피아노|음악|바이올린|첼로|플룻|기타|보컬|뮤직"),
    ("coding", "코딩", r"코딩|소프트웨어|로봇|컴퓨터|프로그래밍"),
]
DAYS = ["월", "화", "수", "목", "금", "토", "일", "공휴일"]


def load(data, key, name):
    p = os.path.join(data, key, name + ".json")
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def tel(t):
    t = str(t or "").strip()
    return "" if not t or re.fullmatch(r"[0-9]{2,3}-?0{3,4}-?0{4}", t) else t   # 02-0000-0000 같은 빈 번호는 숨김


def won(n):
    return f"{n:,}원" if n else ""


def page(c, key, path, title, desc, body, crumbs):
    """공통 틀: 제목·설명·주소 표준·앱으로 가기"""
    site = f"https://{key}.songgollab.co.kr"
    col = c["colors"]
    nav = " › ".join(f'<a href="{u}">{E(t)}</a>' if u else E(t) for t, u in crumbs)
    now = datetime.now(KST).strftime("%Y-%m-%d")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{site}/{path}">
<meta property="og:type" content="website"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{site}/{path}"><meta property="og:image" content="{site}/icon-512.png"><meta property="og:locale" content="ko_KR">
<link rel="icon" href="/icon-192.png">
<style>
:root{{--c:{col['city']};--ink:{col['ink']};--soft:{col['soft']}}}
*{{box-sizing:border-box}}body{{margin:0;background:#F7F5F0;color:#1B2033;font:15px/1.65 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif}}
.w{{max-width:760px;margin:0 auto;padding:18px 16px 40px}}a{{color:var(--ink)}}
.top{{display:flex;align-items:center;gap:10px;margin-bottom:6px}}.top img{{width:36px;height:36px;border-radius:10px}}.top b{{font-size:16px}}.top b span{{color:var(--c)}}
.crumb{{font-size:12.5px;color:#6B7280;margin:6px 0 4px}}.crumb a{{color:#6B7280}}
h1{{font-size:24px;line-height:1.35;margin:6px 0 6px;letter-spacing:-.4px}}h2{{font-size:18px;margin:26px 0 10px}}
.lead{{color:#4B5163;margin:0 0 14px}}.card{{background:#fff;border-radius:16px;padding:14px 16px;margin:10px 0;box-shadow:0 6px 18px -12px rgba(40,30,10,.25)}}
.app{{display:block;text-align:center;background:var(--c);color:#fff;text-decoration:none;font-weight:800;border-radius:14px;padding:13px;margin:16px 0}}
.chips{{display:flex;flex-wrap:wrap;gap:6px}}.chips a{{background:#fff;border-radius:10px;padding:6px 10px;text-decoration:none;font-size:13.5px;box-shadow:0 2px 6px rgba(0,0,0,.06)}}
table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:8px 6px;border-bottom:1px solid #EEF0F4;text-align:left;vertical-align:top}}th{{color:#6B7280;font-weight:700;font-size:12.5px}}
.num{{text-align:right;white-space:nowrap}}.sub{{color:#6B7280;font-size:12.5px}}.kpi{{display:flex;gap:10px;flex-wrap:wrap}}.kpi div{{flex:1;min-width:120px;background:var(--soft);border-radius:12px;padding:10px 12px}}.kpi b{{display:block;font-size:20px;color:var(--ink)}}
footer{{margin-top:28px;font-size:12px;color:#6B7280;line-height:1.7}}
</style></head><body><div class="w">
<div class="top"><img src="/icon-192.png" alt=""><b>아이랑 <span>{E(c['name'])}</span></b></div>
<div class="crumb">{nav}</div>
{body}
<a class="app" href="/">아이랑 {E(c['name'])} 앱으로 보기 — 우리 아이 학교·급식·학원 한곳에</a>
<footer>아이랑은 공공기관이 아닌 송골랩이 만든 무료 서비스예요. 공공데이터(나이스 교육정보 개방포털, 유치원 알리미, 도서관 정보나루, 국립중앙의료원 등)를 모아 보여 드려요.
정보는 바뀔 수 있으니 방문 전 꼭 전화로 확인해 주세요. 마지막 갱신 {now}.</footer>
</div></body></html>"""


def subject_of(a, rx):
    text = a.get("n", "") + " " + " ".join(x[0] for x in a.get("f") or [])
    return re.search(rx, text, re.I) is not None


def fees_of(a, rx):
    return [v for n, v in (a.get("f") or []) if v and 10000 <= v <= 3000000 and (re.search(rx, n, re.I) or re.search(rx, a.get("n", ""), re.I))]


def build_city(key, out, data):
    c = CFG["cities"][key]
    nm, sgg = c["name"], c.get("sgg") or (c["name"] + ("시" if c.get("sido", "경기") == "경기" else "구"))
    root = os.path.join(out, key)
    gd = os.path.join(root, "guide")
    os.makedirs(os.path.join(gd, "academy"), exist_ok=True)
    pages = []

    def write(path, title, desc, body, crumbs):
        p = os.path.join(root, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        pretty = re.sub(r"(index)?\.html$", "", path)   # Cloudflare Pages는 .html 없는 주소로 보여 줌
        doc = page(c, key, pretty, title, desc, body, crumbs)
        doc = re.sub(r'(href="/guide/[^"]*?)\.html"', r'\1"', doc)
        open(p, "w", encoding="utf-8").write(doc)
        pages.append(pretty)

    home = ("아이랑 " + nm, "/guide/")
    aca = (load(data, key, "academies") or {}).get("academies") or []
    kin = (load(data, key, "kinder") or {}).get("kinders") or []
    libs = (load(data, key, "libs") or {}).get("libraries") or []
    hos = load(data, key, "hospitals") or {}
    ev = load(data, key, "events") or {}

    # ── 학원: 과목별 · 동별
    subj_links, sub_pages = [], []
    for slug, label, rx in SUBJECTS:
        lst = [a for a in aca if subject_of(a, rx)]
        if len(lst) < 3:
            continue
        fees = [v for a in lst for v in fees_of(a, rx)]
        med = int(statistics.median(fees)) if fees else 0
        by_dong = {}
        for a in lst:
            by_dong.setdefault(a.get("dong") or "기타", []).append(a)
        dongs = sorted(by_dong.items(), key=lambda kv: -len(kv[1]))
        subj_links.append((slug, label, len(lst)))
        rows = "".join(f"<tr><td><b>{E(a['n'])}</b><div class='sub'>{E(a.get('dong'))}{' · ' + E(tel(a.get('tel'))) if tel(a.get('tel')) else ''}</div></td>"
                       f"<td class='num'>{won(min(fees_of(a, rx)) if fees_of(a, rx) else 0)}</td></tr>"
                       for a in sorted(lst, key=lambda a: (-len(fees_of(a, rx)), a.get("dong", ""), a["n"]))[:80])
        dong_chips = "".join(f'<a href="/guide/academy/{slug}/{E(d)}.html">{E(d)} {len(v)}</a>' for d, v in dongs if d != "기타" and len(v) >= 3)
        body = f"""<h1>{E(sgg)} {E(label)}학원 {len(lst)}곳 · 교습비 비교</h1>
<p class="lead">{E(sgg)}에 등록된 {E(label)} 학원·교습소 {len(lst)}곳을 동네별로 모았어요. 교습비는 교육청에 신고된 금액이에요.</p>
<div class="kpi"><div>학원·교습소<b>{len(lst)}곳</b></div><div>교습비 신고 학원<b>{len({a['id'] for a in lst if fees_of(a, rx)})}곳</b></div>{f'<div>신고 교습비 가운데값<b>{won(med)}</b></div>' if med else ''}</div>
<h2>동네별로 보기</h2><div class="chips">{dong_chips or '<span class="sub">동네별로 나눌 만큼 많지 않아요</span>'}</div>
<h2>학원 목록</h2><div class="card"><table><tr><th>학원</th><th class="num">신고 교습비(최저)</th></tr>{rows}</table>
{'<p class="sub">목록은 80곳까지 보여 드려요. 전체는 앱에서 볼 수 있어요.</p>' if len(lst) > 80 else ''}</div>"""
        write(f"guide/academy/{slug}.html", f"{sgg} {label}학원 {len(lst)}곳 교습비 비교 | 아이랑 {nm}",
              f"{sgg} {label}학원·교습소 {len(lst)}곳의 동네별 목록과 교육청 신고 교습비" + (f"(가운데값 {won(med)})" if med else "") + "를 한눈에 비교해 보세요.",
              body, [home, ("학원", "/guide/academy/"), (label, None)])
        for d, v in dongs:
            if d == "기타" or len(v) < 3:
                continue
            f2 = [x for a in v for x in fees_of(a, rx)]
            m2 = int(statistics.median(f2)) if f2 else 0
            rows2 = "".join(f"<tr><td><b>{E(a['n'])}</b><div class='sub'>{E(a.get('a'))}<br>{E(tel(a.get('tel')))}</div></td><td class='num'>{'<br>'.join(E(n) + ' ' + won(x) for n, x in (a.get('f') or [])[:4])}</td></tr>" for a in sorted(v, key=lambda a: (not a.get('f'), a['n']))[:60])
            body2 = f"""<h1>{E(d)} {E(label)}학원 {len(v)}곳</h1>
<p class="lead">{E(sgg)} {E(d)}의 {E(label)} 학원·교습소 {len(v)}곳이에요.{f' 교육청에 신고된 교습비 가운데값은 {won(m2)}이에요.' if m2 else ''}</p>
<div class="card"><table><tr><th>학원</th><th class="num">신고 교습비</th></tr>{rows2}</table></div>
<p class="sub"><a href="/guide/academy/{slug}.html">← {E(sgg)} {E(label)}학원 전체 보기</a></p>"""
            write(f"guide/academy/{slug}/{d}.html", f"{d} {label}학원 {len(v)}곳 교습비 | 아이랑 {nm}",
                  f"{sgg} {d} {label}학원·교습소 {len(v)}곳 목록과 교육청 신고 교습비" + (f"(가운데값 {won(m2)})" if m2 else "") + ".",
                  body2, [home, ("학원", "/guide/academy/"), (label, f"/guide/academy/{slug}.html"), (d, None)])
    if aca:
        dc = {}
        for a in aca:
            dc[a.get("dong") or "기타"] = dc.get(a.get("dong") or "기타", 0) + 1
        body = f"""<h1>{E(sgg)} 학원·교습소 {len(aca):,}곳</h1>
<p class="lead">{E(sgg)}에 등록된 학원·교습소를 과목과 동네로 나눠 봤어요. 과목을 누르면 교습비도 비교할 수 있어요.</p>
<h2>과목별</h2><div class="chips">{''.join(f'<a href="/guide/academy/{s}.html">{E(l)} {n}</a>' for s, l, n in subj_links)}</div>
<h2>동네별 학원 수</h2><div class="card"><table>{''.join(f'<tr><td>{E(d)}</td><td class="num">{n:,}곳</td></tr>' for d, n in sorted(dc.items(), key=lambda kv: -kv[1])[:30])}</table></div>"""
        write("guide/academy/index.html", f"{sgg} 학원 {len(aca):,}곳 · 과목별 교습비 | 아이랑 {nm}",
              f"{sgg} 학원·교습소 {len(aca):,}곳을 수학·영어·국어 등 과목별, 동네별로 정리하고 교육청 신고 교습비를 비교해요.", body, [home, ("학원", None)])

    # ── 유치원
    if kin:
        rows = "".join(f"<tr><td><b>{E(k['n'])}</b><div class='sub'>{E(k.get('type'))} · {E(k.get('dong'))} · {E(k.get('tel'))}</div></td><td class='num'>{k.get('cap') or ''}</td><td>{E(k.get('time'))}</td></tr>" for k in sorted(kin, key=lambda k: (k.get('type', '')[:2] != '공립', k.get('dong', ''), k['n'])))
        pub = sum(1 for k in kin if (k.get("type") or "").startswith("공립"))
        write("guide/kinder.html", f"{sgg} 유치원 {len(kin)}곳 (공립 {pub}곳) 정원·운영시간 | 아이랑 {nm}",
              f"{sgg} 유치원 {len(kin)}곳(공립 {pub}곳)의 정원, 운영시간, 연락처를 동네별로 정리했어요.",
              f"""<h1>{E(sgg)} 유치원 {len(kin)}곳</h1><p class="lead">공립 {pub}곳, 사립 {len(kin) - pub}곳이에요. 유치원 알리미 자료로 정원과 운영시간을 모았어요.</p>
<div class="card"><table><tr><th>유치원</th><th class="num">정원</th><th>운영시간</th></tr>{rows}</table></div>""", [home, ("유치원", None)])

    # ── 도서관
    if libs:
        rows = "".join(f"<tr><td><b>{E(l['name'])}</b><div class='sub'>{E(l.get('addr'))}<br>{E(l.get('tel'))}</div></td><td>{E(l.get('hours'))}<div class='sub'>휴관 {E(l.get('closed'))}</div></td></tr>" for l in libs)
        write("guide/library.html", f"{sgg} 도서관 {len(libs)}곳 운영시간·휴관일 | 아이랑 {nm}",
              f"{sgg} 공공도서관·어린이도서관 {len(libs)}곳의 운영시간, 휴관일, 연락처를 한눈에 보세요.",
              f"""<h1>{E(sgg)} 도서관 {len(libs)}곳 운영시간·휴관일</h1><p class="lead">공공도서관과 어린이도서관의 운영시간과 휴관일이에요.</p>
<div class="card"><table><tr><th>도서관</th><th>운영시간</th></tr>{rows}</table></div>""", [home, ("도서관", None)])

    # ── 소아청소년과
    peds = [x for x in hos.get("clinics") or [] if "소아청소년과" in (x.get("d") or []) or "소아" in x.get("n", "")]
    if peds:
        def hrs(h):
            h = h or []
            def one(s): return f"{s[:2]}:{s[2:4]}~{s[4:6]}:{s[6:8]}" if s and len(s) == 8 else "휴진"
            return f"평일 {one(h[0] if h else '')} · 토 {one(h[5] if len(h) > 5 else '')} · 일 {one(h[6] if len(h) > 6 else '')}"
        late = [x for x in peds if any(s and len(s) == 8 and s[4:6] >= "20" for s in (x.get("h") or [])[:5])]
        sun = [x for x in peds if len(x.get("h") or []) > 6 and x["h"][6]]
        rows = "".join(f"<tr><td><b>{E(x['n'])}</b><div class='sub'>{E(x.get('a'))}</div></td><td>{hrs(x.get('h'))}</td></tr>" for x in sorted(peds, key=lambda x: (x not in late, x not in sun, x['n'])))
        write("guide/pediatrics.html", f"{sgg} 소아과 {len(peds)}곳 · 야간·일요일 진료 | 아이랑 {nm}",
              f"{sgg} 소아청소년과 {len(peds)}곳의 진료 시간. 저녁 8시 넘어 여는 곳 {len(late)}곳, 일요일에 여는 곳 {len(sun)}곳을 먼저 보여 드려요.",
              f"""<h1>{E(sgg)} 소아청소년과 {len(peds)}곳 진료 시간</h1>
<p class="lead">저녁 8시 넘어 여는 곳 {len(late)}곳, 일요일에 여는 곳 {len(sun)}곳을 위에 보여 드려요. 위급하면 바로 <b>119</b>에 전화하세요.</p>
<div class="kpi"><div>소아청소년과<b>{len(peds)}곳</b></div><div>야간(20시 이후)<b>{len(late)}곳</b></div><div>일요일 진료<b>{len(sun)}곳</b></div></div>
<div class="card"><table><tr><th>병원</th><th>진료 시간</th></tr>{rows}</table></div>""", [home, ("소아과", None)])

    # ── 행사
    today = datetime.now(KST).strftime("%Y-%m-%d")
    evs = [e for e in (ev.get("city") or []) + (ev.get("lib") or []) if (e.get("end") or e.get("start") or "9") >= today]
    if evs:
        rows = "".join(f"<tr><td><b>{E(e['title'])}</b><div class='sub'>{E(e.get('place') or e.get('lib'))}</div></td><td class='num'>{E(e.get('start', '')[5:].replace('-', '/'))}{' ~ ' + E(e.get('end', '')[5:].replace('-', '/')) if e.get('end') and e.get('end') != e.get('start') else ''}</td></tr>" for e in evs[:60])
        write("guide/events.html", f"{sgg} 아이와 갈 만한 곳 · 행사 {len(evs)}개 | 아이랑 {nm}",
              f"{sgg}에서 아이와 함께 갈 만한 공연·축제·체험 프로그램 {len(evs)}개를 날짜순으로 모았어요.",
              f"""<h1>{E(sgg)} 아이와 갈 만한 곳 · 행사</h1><p class="lead">앞으로 열리는 아이·가족 공연, 축제, 체험 프로그램 {len(evs)}개예요.</p>
<div class="card"><table><tr><th>행사</th><th class="num">날짜</th></tr>{rows}</table></div>""", [home, ("행사", None)])

    # ── 도시 안내 (허브)
    links = [("학원·교습비", "/guide/academy/", f"{len(aca):,}곳"), ("유치원", "/guide/kinder.html", f"{len(kin)}곳"),
             ("도서관", "/guide/library.html", f"{len(libs)}곳"), ("소아과 진료 시간", "/guide/pediatrics.html", f"{len(peds)}곳"),
             ("아이와 갈 만한 곳", "/guide/events.html", f"{len(evs)}개")]
    body = f"""<h1>{E(sgg)} 아이 키우는 집을 위한 동네 정보</h1>
<p class="lead">학원·교습비, 유치원, 도서관, 소아과, 아이와 갈 만한 곳을 공공데이터로 모아 매일 새로 고쳐요.</p>
<div class="card"><table>{''.join(f'<tr><td><a href="{u}"><b>{E(t)}</b></a></td><td class="num">{E(n)}</td></tr>' for t, u, n in links)}</table></div>
<h2>과목별 학원</h2><div class="chips">{''.join(f'<a href="/guide/academy/{s}.html">{E(l)}학원 {n}</a>' for s, l, n in subj_links)}</div>"""
    write("guide/index.html", f"{sgg} 학원·유치원·도서관·소아과 정보 | 아이랑 {nm}",
          f"{sgg} 학원 교습비 비교, 유치원, 도서관 운영시간, 소아과 진료 시간, 아이와 갈 만한 곳을 한곳에서 보세요.", body, [home])

    # ── 사이트맵·robots
    site = f"https://{key}.songgollab.co.kr"
    from urllib.parse import quote
    urls = [site + "/"] + [site + "/" + quote(p) for p in pages]
    open(os.path.join(root, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{E(u)}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    open(os.path.join(root, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {site}/sitemap.xml\n")
    return len(pages)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=os.path.join(os.path.dirname(HERE), "data"))
    ap.add_argument("--city", action="append")
    a = ap.parse_args()
    tot = 0
    for k in a.city or list(CFG["cities"]):
        if not os.path.isdir(os.path.join(a.out, k)):
            continue
        n = build_city(k, a.out, a.data); tot += n
    ent = os.path.join(a.out, "entry")
    if os.path.isdir(ent):   # 입구(airang.songgollab.co.kr): 사이트맵·robots
        today = datetime.now(KST).strftime("%Y-%m-%d")
        # 사이트맵 묶음: 입구 + 모든 도시 사이트맵 (구글 '도메인' 등록이면 다른 하위 주소 사이트맵도 한 번에 받음)
        open(os.path.join(ent, "sitemap.xml"), "w", encoding="utf-8").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"<url><loc>https://airang.songgollab.co.kr/</loc><lastmod>{today}</lastmod></url>\n</urlset>\n")
        open(os.path.join(ent, "sitemap-all.xml"), "w", encoding="utf-8").write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"<sitemap><loc>https://{k}.songgollab.co.kr/sitemap.xml</loc><lastmod>{today}</lastmod></sitemap>\n" for k in CFG["cities"])
            + "<sitemap><loc>https://airang.songgollab.co.kr/sitemap.xml</loc></sitemap>\n</sitemapindex>\n")
        open(os.path.join(ent, "robots.txt"), "w", encoding="utf-8").write("User-agent: *\nAllow: /\nSitemap: https://airang.songgollab.co.kr/sitemap.xml\n")
    print(f"검색용 페이지 {tot}개")
