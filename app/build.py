"""아이랑 앱 만들기 — 원본(템플릿) 1벌 + 도시 설정(cities.json) → 도시별 앱 폴더.

  python3 app/build.py                 # out/<도시>/ 에 7개 앱을 만든다
  python3 app/build.py --out 폴더       # 다른 곳에 만들기
  python3 app/build.py --city yongin   # 한 도시만 (--city entry = 입구)

템플릿 문법 (줄 단위)
  {{name}} {{key}} {{c.city}} …           도시 설정 값으로 바뀜 (cities.json)
  {{#if yongin}} … {{#elif suwon,anyang}} … {{#elif seoul}} … {{#else}} … {{/if}}
                                          (seoul / gyeonggi = 그 시도의 모든 도시)
                                          그 도시일 때만 들어가는 줄 (#if 줄은 한 줄 전체)
"""
import argparse, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "cities.json"), encoding="utf-8"))
# 시도: 이름 → (정식 이름, 템플릿 태그, 시군구 끝 글자). 순서 = 다른 도시 둘러보기·입구 탭 순서
SIDOS = {"경기": ("경기도", "gyeonggi", "시"), "서울": ("서울특별시", "seoul", "구"),
         "인천": ("인천광역시", "incheon", "구"), "충남": ("충청남도", "chungnam", "시")}
SIDO_ORDER = list(SIDOS)
TEMPLATES = ["index.html", "sw.js", "manifest.webmanifest", "404.html"]
COND = re.compile(r"^\{\{#(if|elif) ([a-z,]+)\}\}$|^\{\{#else\}\}$|^\{\{/if\}\}$")


def tokens(city):
    c = CFG["cities"][city]
    t = {"key": city, "name": c["name"]}
    for k, v in c.get("colors", {}).items():
        t["c." + k] = v
    for k, v in c.get("fields", {}).items():
        t["f." + k] = v
    # 도시마다 다른 값 (cities.json 에서 만들어 냄)
    g = c.get("gus", [])
    t["f.gus"] = json.dumps(g, ensure_ascii=False)
    tiles = ["t-mint", "t-indigo", "t-coral", "t-sun", "t-lilac"]
    t["f.tileCls"] = "{ " + ", ".join(f'"{x}": "{tiles[i % len(tiles)]}"' for i, x in enumerate(g)) + " }"
    t["f.searchEx"] = c.get("searchEx", "")
    # 시도 (경기 / 서울): 서울은 구 하나가 앱 하나 → 시군구 이름이 '강남구'
    sido = c.get("sido", "경기")
    t["f.sidoShort"] = sido
    t["f.sidoFull"] = SIDOS[sido][0]
    t["f.sgg"] = c.get("sgg", c["name"] + SIDOS[sido][2])
    # 다른 도시 둘러보기: [이름, 주소, 시도] — 경기도 → 서울, 시도 안에서는 가나다순
    oc = sorted(CFG["cities"].items(), key=lambda kv: (SIDO_ORDER.index(kv[1].get("sido", "경기")), kv[1]["name"]))
    oc = [f'["{v["name"]}", "https://{k}.songgollab.co.kr", "{v.get("sido", "경기")}"]' for k, v in oc]
    t["f.otherCities"] = "const OTHER_CITIES = [\n  " + ",\n  ".join(", ".join(oc[i:i + 6]) for i in range(0, len(oc), 6)) + "];"
    return t


def tags(city):
    """{{#if …}} 에 쓸 수 있는 이름: 도시 키 + 시도 묶음 (gyeonggi / seoul / incheon / chungnam)
    + nojobs (엄마 일자리 자료가 없는 시도 = 경기 밖 전부)"""
    sido = CFG["cities"][city].get("sido", "경기")
    t = {city, SIDOS[sido][1]}
    if sido != "경기": t.add("nojobs")
    return t


def render(text, city):
    out, stack = [], []          # stack: [이 블록에서 이미 맞은 것이 있나, 지금 줄을 넣나]
    lines = text.split("\n")
    for ln in lines:
        m = COND.match(ln)
        if m:
            if ln.startswith("{{#if"):
                hit = bool(tags(city) & set(m.group(2).split(","))); stack.append([hit, hit])
            elif ln.startswith("{{#elif"):
                top = stack[-1]; hit = not top[0] and bool(tags(city) & set(m.group(2).split(","))); top[1] = hit; top[0] = top[0] or hit
            elif ln == "{{#else}}":
                top = stack[-1]; top[1] = not top[0]; top[0] = True
            else:
                stack.pop()
            continue
        if all(s[1] for s in stack):
            out.append(ln)
    assert not stack, "{{#if}} 블록이 닫히지 않았어요"
    s = "\n".join(out)
    t = tokens(city)
    def sub(m):
        k = m.group(1)
        if k not in t: raise KeyError(f"{city}: 설정에 없는 값 {{{{{k}}}}}")
        return t[k]
    return re.sub(r"\{\{([a-z]+(?:\.[A-Za-z0-9_]+)?)\}\}", sub, s)


NAVER = json.load(open(os.path.join(HERE, "naver.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "naver.json")) else {}

def build(city, out):
    d = os.path.join(out, city)
    if os.path.exists(d): shutil.rmtree(d)
    os.makedirs(d)
    for f in TEMPLATES:
        src = os.path.join(HERE, f)
        if not os.path.exists(src): continue
        if f == "404.html" and not CFG["cities"][city].get("has404"): continue
        txt = render(open(src, encoding="utf-8", newline="").read(), city)
        if f == "index.html" and NAVER.get(city):                                     # 네이버 서치어드바이저 소유확인 (도시마다 다름 → app/naver.json)
            txt = txt.replace('<meta charset="utf-8">', f'<meta charset="utf-8">\n<meta name="naver-site-verification" content="{NAVER[city]}" />', 1)
        open(os.path.join(d, f), "w", encoding="utf-8", newline="").write(txt)
    shutil.copytree(os.path.join(HERE, "assets"), os.path.join(d, "assets"))          # 모든 도시 같은 그림
    own = os.path.join(HERE, "cities", city)                                             # 도시 그림·아이콘
    for f in os.listdir(own):
        dst = os.path.join(d, "assets", f) if f.startswith("hero-") else os.path.join(d, f)
        shutil.copy(os.path.join(own, f), dst)
    return d


def build_entry(out):
    """입구(airang.songgollab.co.kr): 도시 고르기 화면. 도시 카드는 cities.json 에서."""
    d = os.path.join(out, "entry")
    if os.path.exists(d): shutil.rmtree(d)
    os.makedirs(os.path.join(d, "img"))
    rows = [[k, c["name"], c["colors"]["city"], c.get("areas", ""), c.get("lat", 0), c.get("lon", 0), c.get("sido", "경기")] for k, c in CFG["cities"].items()]
    src = open(os.path.join(HERE, "entry", "index.html"), encoding="utf-8").read()
    assert "/*CITIES*/[]" in src
    src = src.replace("/*CITIES*/[]", json.dumps(rows, ensure_ascii=False))
    # 검색용 페이지로 가는 링크 (검색 로봇이 따라가도록 HTML에 바로 적음)
    g = ""
    for sd, label in (("경기", "경기도"), ("서울", "서울"), ("인천", "인천"), ("충남", "충남")):
        cs = sorted([(k, c) for k, c in CFG["cities"].items() if c.get("sido", "경기") == sd], key=lambda kc: kc[1]["name"])
        if cs:
            g += f'<p>{label}</p>' + "".join(f'<a href="https://{k}.songgollab.co.kr/guide/">{c.get("sgg") or c["name"] + SIDOS[sd][2]} 학원·유치원·소아과</a>' for k, c in cs)
    src = src.replace("<!--GUIDES-->", f'<div class="lift guides"><h3>📍 동네 정보 모아보기</h3>{g}</div>')
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(src)
    for f in ("icon-192.png", "icon-512.png"):
        shutil.copy(os.path.join(HERE, "entry", f), d)
    for k in CFG["cities"]:
        own = os.path.join(HERE, "cities", k)
        shutil.copy(os.path.join(own, f"hero-{k}-800.webp"), os.path.join(d, "img"))
        shutil.copy(os.path.join(own, "icon-192.png"), os.path.join(d, "img", f"ic-{k}.png"))
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out"))
    ap.add_argument("--city", action="append")
    a = ap.parse_args()
    for c in a.city or list(CFG["cities"]) + ["entry"]:
        print("만듦:", build_entry(a.out) if c == "entry" else build(c, a.out))
