"""아이랑 앱 만들기 — 원본(템플릿) 1벌 + 도시 설정(cities.json) → 도시별 앱 폴더.

  python3 app/build.py                 # out/<도시>/ 에 7개 앱을 만든다
  python3 app/build.py --out 폴더       # 다른 곳에 만들기
  python3 app/build.py --city yongin   # 한 도시만

템플릿 문법 (줄 단위)
  {{name}} {{key}} {{c.city}} …           도시 설정 값으로 바뀜 (cities.json)
  {{#if yongin}} … {{#elif suwon,anyang}} … {{#else}} … {{/if}}
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
    return t


def render(text, city):
    out, stack = [], []          # stack: [이 블록에서 이미 맞은 것이 있나, 지금 줄을 넣나]
    lines = text.split("\n")
    for ln in lines:
        m = COND.match(ln)
        if m:
            if ln.startswith("{{#if"):
                hit = city in m.group(2).split(","); stack.append([hit, hit])
            elif ln.startswith("{{#elif"):
                top = stack[-1]; hit = not top[0] and city in m.group(2).split(","); top[1] = hit; top[0] = top[0] or hit
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out"))
    ap.add_argument("--city", action="append")
    a = ap.parse_args()
    for c in a.city or CFG["cities"]:
        print("만듦:", build(c, a.out))
