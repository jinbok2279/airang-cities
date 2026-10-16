# airang-cities — 아이랑 도시별 앱·수집 (경기도 확장용 공통 저장소)

| 도시 | 앱 | 데이터 | 임시 주소 |
|---|---|---|---|
| 성남 | apps/seongnam | data/seongnam | https://airang-seongnam.pages.dev |
| 안양 | apps/anyang | data/anyang | https://airang-anyang.pages.dev |
| 고양 | apps/goyang | data/goyang | https://airang-goyang.pages.dev |
| 화성 | apps/hwaseong | data/hwaseong | https://airang-hwaseong.pages.dev |
| 부천 | apps/bucheon | data/bucheon | https://airang-bucheon.pages.dev |

- 도시 설정은 `city.py` 한 곳. 새 도시는 여기 한 칸 + 앱 폴더 + 워크플로 목록에 추가.
- 수집: `daily.yml`(매일 05:30), `weather.yml`(하루 4번). 데이터는 `data/<도시>/`.
- 배포: `apps/**` 가 바뀌면 `deploy.yml`이 Cloudflare Pages(airang-<도시>)로 올림. 앱은 데이터를 이 저장소 raw 주소에서 읽음.
- Secrets: NEIS_KEY, KINDER_KEY, LIB_KEY, WEATHER_KEY, KOPIS_KEY, TOUR_KEY, CULTURE_KEY, CLOUDFLARE_API_TOKEN, (선택) KAKAO_KEY
- 용인·수원은 각자 저장소(yongin / yongin-edu-collector / suwon-edu-collector)에서 그대로 운영.
