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
    t["f.sidoFull"] = {"경기": "경기도", "서울": "서울특별시"}[sido]
    t["f.sgg"] = c.get("sgg", c["name"] + ("구" if sido == "서울" else "시"))
    oc = [f'["{v["name"]}", "https://{k}.songgollab.co.kr"]' for k, v in CFG["cities"].items()]
    t["f.otherCities"] = "const OTHER_CITIES = [" + ", ".join(oc[:3]) + ",\n  " + ", ".join(oc[3:]) + "];"
    return t


def tags(city):
    """{{#if …}} 에 쓸 수 있는 이름: 도시 키 + 시도 묶음 (gyeonggi / seoul)"""
    return {city, {"경기": "gyeonggi", "서울": "seoul"}[CFG["cities"][city].get("sido", "경기")]}


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


def build(city, out):
    d = os.path.join(out, city)
    if os.path.exists(d): shutil.rmtree(d)
    os.makedirs(d)
    for f in TEMPLATES:
        src = os.path.join(HERE, f)
        if not os.path.exists(src): continue
        if f == "404.html" and not CFG["cities"][city].get("has404"): continue
        txt = render(open(src, encoding="utf-8", newline="").read(), city)
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
