# 아이랑 앱 원본 (7개 도시 공통, 1벌)

2026-10-29부터 아이랑 앱 7개(용인·수원·성남·안양·고양·화성·부천)는 **이 폴더 하나에서** 만들어요.
예전 앱 폴더(`yongin` 저장소, `suwon-edu-collector/docs`, `airang-cities/apps/*`)는 더 이상 배포에 쓰지 않아요.

## 들어 있는 것
| 파일 | 뜻 |
|---|---|
| `index.html` | 앱 화면 (템플릿). 도시마다 다른 곳은 `{{name}}`, `{{c.city}}` 같은 값이나 `{{#if yongin}} … {{/if}}` 블록 |
| `sw.js`, `manifest.webmanifest`, `404.html` | 오프라인·홈 화면 설치·없는 페이지 (템플릿) |
| `cities.json` | 도시 설정: 이름·색(city/ink/deep/soft)·주소·Cloudflare 이름 |
| `assets/` | 모든 도시 같은 그림 (메뉴 아이콘 등) |
| `cities/<도시>/` | 그 도시만의 그림: 풍경(hero-*.webp), 바로가기 아이콘(icon-192/512.png) |
| `build.py` | 위를 합쳐 `out/<도시>/` 7개를 만듦 |

## 고칠 때
1. `index.html` 을 한 번만 고친다 (7곳 공통). 한 도시만 다르게 하려면 `{{#if 도시}} … {{#else}} … {{/if}}`.
2. `python3 app/build.py --out /tmp/out` 으로 만들어 미리보기.
3. 버전: `index.html` 의 `APP_VER` 한 곳, `sw.js` 의 `CACHE` 숫자.
4. main 에 올리면 airang-stats 의 `cf-apps.yml` 이 매시 7분(또는 수동 실행)에 만들어서 바뀐 도시만 Cloudflare 에 올려요.

## 새 도시 추가
`cities.json` 에 도시 블록 추가 + `cities/<도시>/` 에 풍경·아이콘 + 데이터 수집(`city.py`) → Cloudflare 에 `airang-<도시>` 와 주소 연결.
