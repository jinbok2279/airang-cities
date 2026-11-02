import json, os, urllib.parse, urllib.request, collections
WK = urllib.parse.unquote(os.environ["WEATHER_KEY"])
rows=[]
for page in range(1,4):
    with urllib.request.urlopen("http://api.data.go.kr/openapi/tn_pubr_public_lbrry_api?" + urllib.parse.urlencode({"serviceKey": WK, "type": "json", "pageNo": page, "numOfRows": 1000, "ctprvnNm": "인천광역시"}), timeout=90) as r:
        d=json.loads(r.read().decode("utf-8","replace"))
    it=d["body"]["items"]["item"] if isinstance(d["body"]["items"],dict) else d["body"]["items"]
    rows+=it; print("page",page,len(it),d["body"].get("totalCount"))
    if len(it)<1000: break
print(collections.Counter(r.get("lbrrySe") for r in rows))
print(collections.Counter(r.get("signguNm") for r in rows if r.get("lbrrySe")!="작은도서관"))
print(json.dumps(rows[0],ensure_ascii=False)[:900])
