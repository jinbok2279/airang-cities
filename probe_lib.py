import json, os, urllib.parse, urllib.request
WK = urllib.parse.unquote(os.environ["WEATHER_KEY"])
for base in ("http://api.data.go.kr/openapi/tn_pubr_public_lbrry_api", "https://api.data.go.kr/openapi/tn_pubr_public_lbrry_api"):
    for sg in ("계양구", "미추홀구"):
        try:
            with urllib.request.urlopen(base + "?" + urllib.parse.urlencode({"serviceKey": WK, "type": "json", "pageNo": 1, "numOfRows": 100, "ctprvnNm": "인천광역시", "signguNm": sg}), timeout=60) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            body = d.get("response", {}).get("body", {}); items = body.get("items") or []
            print(base[:12], sg, "전체", body.get("totalCount"), [i.get("lbrryNm") for i in items][:15]); 
            if items: print("  칸:", list(items[0].keys()))
        except Exception as e:
            print(base[:12], sg, "실패", str(e)[:80])
