import os, urllib.request, socket, time
K = os.environ["SEOUL_KEY"].strip()
for host in ("openapi.seoul.go.kr",):
    try: print("DNS", socket.gethostbyname(host))
    except Exception as e: print("DNS 실패", e)
for i in range(3):
    try:
        with urllib.request.urlopen(f"http://openapi.seoul.go.kr:8088/{K}/json/culturalEventInfo/1/1/", timeout=30) as r:
            print("성공", r.status, r.read()[:80]); break
    except Exception as e:
        print("실패", type(e).__name__, str(getattr(e, "reason", e))[:80].replace(K, "***")); time.sleep(5)
