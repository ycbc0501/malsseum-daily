# Saint Seoul (@saintseoul_studio) — daily 말씀 auto-poster

This repo runs a fully hands-off Korean daily Bible-verse Instagram account for the
**Saint Seoul** brand (@saintseoul_studio, renamed 2026-08-13 from @to_light_bible).
The numeric `IG_USER_ID` is unchanged by the rename, so nothing in the API path breaks;
the handle is never hardcoded (`post_instagram.username()`).

**Before making ANY change to the posting pipeline, read [RULES.md](RULES.md) — the single
authority — and verify every rule there still holds after your change.** If a rule intentionally
changes, update RULES.md in the same commit so it never drifts from the code. New rules go in
RULES.md; a rule that lives only in a code comment is a rule the next person will not find.
Run `python3 check_rules.py` afterwards — it checks that each rule in RULES.md is actually
enforced by the code, and a rule that is written down but not enforced reads as a guarantee.

[CONTENT_RULE.md](CONTENT_RULE.md) holds the reasoning, history and measurements behind those
rules — read it when you need to know *why*. **Where the two disagree, RULES.md wins.**

## 현재 상태 — 2026-10-07, 제재 해제 확인 (읽고 시작할 것)

**[notes/strategy/STRATEGY.md](notes/strategy/STRATEGY.md)** 가 지금 이 계정의 제1 문서다.
**§13을 먼저 읽을 것 — 10-07에 전제가 하나 뒤집혔다.**

- **2026-10-07 계정 상태 화면: 전 항목 ✅, 「추천 요건」 포함.** 09-14/09-20에 걸려 있던
  "팔로워가 아닌 사람에게 추천될 수 없습니다"가 **풀렸다.** 「검토 요청」을 누르지 않았는데도
  롤링 30일 창이 자동 재판정된 것으로 보인다. → §7.1·§12의 "원본성 1순위"는 **격하**된다.
- 그러나 **10-02~04 좋아요 급등(37/38/41)은 10-05부터 꺼졌다**(8/23/9). n=3일 돌출이었다.
  이전 세션의 "곡선이 꺾였다"는 과장이었다. 자축 금지.
- 유효하게 남은 것: 릴 도달 ≈ 팔로워 수 · 좋아요율 7~14%(본 사람은 좋아한다) ·
  전달(send) 설계 부재 · 카톡에 못 들어가는 포맷 · **과금 Veo 초의 62.7%가 버려짐**.

## 2026-10-07 오후 — **도달이 3배가 됐다. 공유 수는 내내 화면에 있었다** (STRATEGY.md §14)

원석님 스크린샷 3장이 전제 두 개를 깼다. **API가 `(#10)`으로 거부하는 것과 "볼 수 없다"는
다르다** — 게시물 화면에 조회수(「311회」)·공유(✈️ 보내기)·리포스트(🔁)가 처음부터 다 있었다.
"좋아요만 보고 전략을 세웠다"고 두 달 쓴 동안 숫자는 화면에 있었다. 규칙 **G-2** 신설.
```
제재 중 (09-12~09-18, n=11)  조회 중앙값 103  범위  57~222  팔로워 대비 0.52x
해제 후 (10-05~10-06, n=3)   조회 중앙값 311  범위 252~465  팔로워 대비 1.46x
9월 최대 222 < 10월 최소 252 — 중첩 0. 단측 p=1/C(14,3)=0.003. n=3인데 유의.
```
**0.52x → 1.46x 는 1.0을 넘는다 = 비팔로워에게 배포되고 있다.** 단, 그 사이 변경이 제재 해제만은
아니다(10-01 프레임 검사, 10-06 여백 게이트) — 귀속은 주장할 수 없고 **현재 상태**만 확실하다.
- **좋아요율 7~14% "매우 높다"는 격하.** 그건 팔로워만 보던 기간의 값이었다. 지금 2.6/8.3/8.6%.
  분모에 처음 보는 사람이 들어와서 떨어지는 것이고 건강한 신호다.
- **"아무도 전달하지 않는다"는 틀렸다.** 요청한 적 없는데 공유 0/1/5 (비율 0/0.40/1.08%).
  → **이 3건이 말씀 카드의 사전(before) 측정값이다.** 효과는 "0→1"이 아니라 "1.08%→얼마".
- 넣은 것: `metrics.py observe "<ref>" views=465 likes=40 shares=5 reposts=1` (필드별 `_manual`
  표시, `refresh()`가 실값 받으면 표시까지 삭제). **`report()` 버그도 고쳤다** — `reach`가 없으면
  손입력 14건을 통째로 못 보고 "0 with insights"라고 했다. 이제 `views`를 대리 분모로 쓰고
  **그렇다고 명시**한다.

**사람만 할 수 있는 것:** ①`IG_INSIGHTS_TOKEN` 발급(`ig_login.py`) ②**그 전에도 공짜** —
게시물 열어 `조회/좋아요/공유(✈️)/리포스트(🔁)` 네 숫자만 보내주면 원장에 들어간다.
**10건만 더 모이면** 지금 전략 전체가 서 있는 "좋아요"라는 대리 지표를 도달로 갈아끼울 수 있다.

## 2026-10-07 밤 — **「릴스 인사이트」를 열었다. 병목이 첫 2초로 이동했다** (STRATEGY.md §15)

§14를 쓴 지 몇 시간 만에 **같은 교훈이 한 층 더 밑에서 반복됐다** — 게시물 화면을 찾아낸 뒤에도
그 안의 「인사이트 보기」는 열지 않았다. 거기에 `reach`가 있다. **"이 토큰으로 도달은 영원히
못 본다"는 API에 대해서만 참이었다.** 대상: 고린도전서 10:24 (10-06, `segments:0` 정지 30초).
```
조회 260  조회한 사람 233  평균 조회 2초  팔로우 0   좋아요 22 댓글 2 공유 1 저장 6 리포스트 0
건너뛰기 85.2%(또래보다 높음=나쁨)   공유 0.4%🟢   좋아요 9.3%(또래보다 낮음)   저장 2.5%
출처 — 릴스 탭 56.6% · 탐색 탭 30.9% · 피드 12.5%
```
- **분모를 먼저 검증했다:** 화면 비율 = 값/도달(233). **인스타그램도 도달을 분모로 쓴다** →
  이제 우리 계산과 같은 분모 위에 선다.
- **유통은 변명이 끝났다.** 탐색 탭 30.9% = 비팔로워 발견 표면, 추론이 아니라 라벨.
  도달 233 / 팔로워 214 = 1.09x. **그런데 2초 만에 넘긴다**(2/30초 = 6.7% 시청, 루프 1.12회).
  문제는 "안 보여준다"가 아니라 **"보여주는데 안 본다"** 다.
- **또 뒤집힌 주장 둘:** 「좋아요율 7~14% 매우 높다」 → 인스타그램 판정 **또래보다 낮음**(완전 폐기).
  「전달 설계 부재」 → 공유 0.4%는 **또래보다 높음**. 말씀 카드는 약점 보완이 아니라 **강점 확대**다
  (방향 유지, 근거 교체, **1순위는 아님**). **새 1순위 = 건너뛰기** — 유일한 "또래보다 나쁨".
- **§14.7 길이 논쟁 재판정:** 비교 대상이던 그 30초 정지 사진이 바로 85.2% 건너뛴 건이다.
  움직임 유무 문제가 아니다 → **E-0c/E-0d 유지.** 단 n=1, 판정 기준은 §14.7 그대로.
- **반증된 유혹:** "글씨가 흐려서"는 원장이 깬다 — `text_contrast` 94건 중앙값 10.16인데
  좋아요 최고(42)가 최솟값 1.10. **대비는 반응을 예측하지 못한다.**

**코드:** `observe`가 `reach·watch·skip_rate·src_reels/explore/feed·follows`를 받는다.
`_FIELD_STORE`가 **화면 이름 → API 이름**을 변환(`saves`→`saved`, `watch`초→ms). `report()`
버그 둘 — `saves=6`이 기록 즉시 안 보였고, "views를 분모로 쓴다" 경고가 첫 도달값에 조용해졌다.
희소 평균에 `(n=k)`. `RULES.md` G-2 §5~§7 · `check_rules.py` 6개 · **`test_observe.py` 22개**
(역테스트 확인: 매핑 되돌리면 4개, 퍼센트 int로 자르면 7개 실패).

**다음 4건은 「인사이트 보기」까지 — 조회한 사람·평균 조회 시간·건너뛰기·조회 출처.**
3~4건이면 85.2%가 상수인지 이 한 건인지 갈린다: 이사야 42:12 · 이사야 12:5 · 로마서 16:27 ·
디모데전서 2:4 (전부 7.67초 릴).

**비용 — 2026-10-07 수정 완료 ✅.** STRATEGY.md §6의 수정안을 구현했다(`RULES.md` E-0c·E-0d,
`daily_post.CHAIN_TRIES = 1` + `chain_ok` 게이트, `test_veo_budget.py`). **오프닝이 1회에
검사를 통과하지 못하면 연결을 아예 시작하지 않고, 연결은 take 1회뿐이다.** 근거: 09-23 이후
25건에서 과금 초의 62.7%가 버려졌고(1,008초 사서 376초 출고), 호출이 가장 많은 글이 가장 짧은
릴을 냈으며, 길이는 반응과 무관했다(8/15/23초 → 21.9/27.2/26.3 좋아요, 구간 중첩).
```
게시 1건 최악의 경우   9호출 72초 ₩597,576/월  →  3호출 24초 ₩199,192/월
실측(최근 25건 평균)   39.0초 = ₩324,019/월     ← 다음 게시물부터 내려간다
```
`test_veo_budget.py`가 **상한을 원 단위로 계산해 한도와 비교**하고, 누수를 되돌리는 변경에서
실패한다(역테스트 확인). 아직 안 한 것: **저녁 슬롯 폐지**(§9.1) — 하면 Veo가 다시 반이 되지만
발행 빈도 결정이라 승인 대기 중.

Pipeline entry point: `daily_post.py` (orchestrator) → `fetch_higgsfield.py` (image + gates),
`fetch_veo.py` (motion), `fetch_lyria.py` (music), `make_video.py` (reel), `generate.py` (text),
`post_instagram.py` (publish — and it is the CLI, not `daily_post.py`, that actually
publishes in CI). No-repeat ledgers live in `state.json`; performance in `metrics.json`
(`metrics.py`, backfilled by `insights.py`); comment replies in `comments.json`.
