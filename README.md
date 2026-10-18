# 로또신령 홈페이지

https://bandouni33.github.io — 회차별 로또 당첨번호, 번호 통계, 실수령액 계산, 이번 주 신령 타로.

- 데이터: 앱 저장소 `bandouni33/lotto-shinryeong` 의 `site_data/data.json`(공식 당첨번호 등 공개 값만)
- 생성: `python build.py --data <data.json> --assets <앱 저장소> --out _site`
- 배포: `.github/workflows/deploy.yml` (토요일 밤 3회 + 매일 1회 + push)
- 네이버·구글 소유확인: `naver_verification.txt` / `google_verification.txt` 에 메타태그 content 값만 넣고 push
- 이 저장소에는 비밀키를 두지 않는다.
