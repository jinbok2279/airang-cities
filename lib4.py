"""도서관 정보나루(data4library.kr) Open API 공통 도구

시 도서관 홈페이지가 자동 수집을 막아 두어서, 국립중앙도서관이 운영하는
'도서관 정보나루' 공식 API로 도시 공공도서관 정보와 대출 순위를 받는다.
API 키는 저장소 Secrets 의 LIB_KEY 에 넣는다 (data4library.kr 회원가입 → 인증키 신청, 무료).
"""

import json
import os
import time
import urllib.parse
import urllib.request

KEY = os.environ.get("LIB_KEY", "").strip()
API = "https://data4library.kr/api/"  # 키가 평문으로 오가지 않게 https 우선
API_HTTP = "http://data4library.kr/api/"  # https가 막히면 예비
REGION = 31  # 경기도
from city import C
GU = C["lib"]  # 정보나루 세부지역 코드 (행정구역 코드와 다름)
UA = {"User-Agent": "Mozilla/5.0 (seongnam-edu-collector)"}


def call(name, **params):
    """정보나루 API 호출 → response 딕셔너리. 오류면 RuntimeError."""
    q = dict(params, authKey=KEY, format="json")
    last = None
    for i in range(3):
        url = (API if i < 2 else API_HTTP) + name + "?" + urllib.parse.urlencode(q)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as res:
                data = json.loads(res.read().decode("utf-8"))
            resp = data.get("response", {})
            if resp.get("error"):
                raise RuntimeError(resp["error"])
            return resp
        except Exception as e:
            last = e
            print(f"  {name} 다시 시도 {i + 1}/3: {str(e).replace(KEY, '***') if KEY else e}")
            time.sleep(4)
    raise RuntimeError(f"{name} 실패: {last}")


def items(resp, outer, inner):
    """{'docs': [{'doc': {...}}]} 모양에서 안쪽 딕셔너리만 꺼내기"""
    out = []
    for x in resp.get(outer) or []:
        if isinstance(x, dict):
            out.append(x.get(inner, x))
    return out
