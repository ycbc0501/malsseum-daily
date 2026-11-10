# Saint Seoul (@saintseoul_studio) — daily 말씀 auto-poster

This repo runs a fully hands-off Korean daily Bible-verse Instagram account for the
**Saint Seoul** brand (@saintseoul_studio, renamed 2026-08-13 from @to_light_bible).
The numeric `IG_USER_ID` is unchanged by the rename, so nothing in the API path breaks;
the handle is never hardcoded (`post_instagram.username()`).

## ⛔ 먼저 — 절대 건드리지 않는 것

**`wonsukwaynelee` 는 계정 주인의 개인 인스타그램 계정입니다. 프로페셔널 계정으로
전환하지 않습니다. 어떤 상황에서도. 전환은 되돌릴 수 없습니다.**

2026-11-02에 누를 뻔했습니다 — Instagram 비즈니스 로그인 승인 주소는 **브라우저의 활성
세션**을 그대로 쓰고 어느 계정인지 묻지 않습니다. 활성 계정이 `wonsukwaynelee` 였고
개인 계정이라 「Change to professional account?」 버튼이 떴습니다.
**승인 주소를 열기 전에 활성 계정이 @saintseoul_studio 인지 먼저 확인하십시오.**
자세한 것과 그 밖의 되돌릴 수 없는 계정 변경은 [RULES.md](RULES.md) **0절**.

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

## 2026-10-07 심야 — **API로 못 받는 게 아니었다. 권한 하나였다** (STRATEGY.md §16)

원석님 지적("독스 똑바로 다시봐")이 맞았다. **`debug_token` 한 번이면 끝날 일이었다.**
```
scopes: pages_show_list · instagram_basic · instagram_manage_comments
        instagram_content_publish · pages_read_engagement · public_profile
→ instagram_manage_insights 가 없다. 요청된 적이 없다.
```
`(#10)`은 **"인스타그램이 숨긴다"가 아니라 "이 토큰은 요청한 적이 없다"** 였다. 메시지는
처음부터 정확했다. §14=게시물 화면 안 봄, §15=인사이트 안쪽 안 엶, **§16=에러 메시지 안 읽음.**

- **"매번 수동"이 아니다. 어제 손으로 넣은 13칸 → 자동 10칸 + 수동 3칸.**
  공식 릴 지표에 **`reels_skip_rate`와 `reposts`가 있다** — §15가 1순위로 지목한 건너뛰기가
  API에 있었다. 수동으로 남는 건 **조회 출처 · 또래 비교 · 미디어 팔로우 셋뿐**이고
  전부 천천히 변해서 2주에 한 건이면 된다.
- **권한이 생겼어도 안 들어왔을 것 — 둘은 우리 탓이다.** ① `INSIGHT_TIERS`가
  `reels_skip_rate·reposts`를 한 번도 요청한 적이 없다. ② `insights.py api()`는 읽기 토큰이
  `graph.instagram.com`에만 유효한 걸 아는데 `post_instagram.insights()`에 **전달하지 않았다**
  → OAuth 실패 → `{}` → 로그 "insights unavailable" = 권한 없을 때와 동일. **승인해도 헛수고.**
- **내 지난 "확인"은 무효였다.** authorize URL `200`은 **존재하지 않는 앱 ID에도 똑같이** 온다
  (본문 680,448 vs 680,370). 그리고 **권한이 없으면 Meta는 가짜 지표 이름에도 `(#10)`** 을
  돌려준다(`view_sources`로 확인) → **`(#10)` 쓸어보기로 지표 유무 판정 불가.**

**코드:** **`ig_doctor.py` 신규** — 한 줄로 권한·빠진 것·자동/수동 경계를 출력(추측 금지).
`INSIGHT_TIERS`+`INSIGHT_SINGLES` 보강, `insights(…, base=)`. **G-2.6이 쓰인 지 몇 시간 만에
제 코드를 잡았다** — 손입력 `skip_rate` ↔ API `reels_skip_rate` 어긋남, 매핑+이관 완료.
⚠️ **API가 85.2를 주는지 0.852를 주는지는 미지** — 첫 실값을 손입력과 대조 전엔 안 믿는다.
`RULES.md` G-2 1-a~1-d · `check_rules.py` 6개 · `test_insight_metrics.py` 12개
(역테스트 4종: 4/1/1/5개 실패 확인).

**원석님 1회 작업** — 자동 갱신 워크플로는 **이미 있다**. 최초 승인만 남았다:
`ig_login.py --auth-url` → 승인 → `--code` → `gh secret set IG_INSIGHTS_TOKEN` →
**`python3 ig_doctor.py`로 확인.** 절차: [notes/insights-token-2026-10-07.md](notes/insights-token-2026-10-07.md)
비즈니스 관리자 경로(SMS 2FA에 막혔던)가 풀렸다면 그쪽이 더 낫다 — 만료 없는 토큰 하나.

## 2026-10-07 심야 2 — **전수 수집. 그리고 권한 없이도 오고 있었다** (STRATEGY.md §17)

원석님 지시: **"독스에 있는 거 다 받고 거기서 우리가 쓸 걸 정해. 예외 두지 말고."**
§16의 "권한 하나만 승인하면 10칸 자동"도 **또 일부만 맞았다.** 독스를 전수로 읽고 실제로 쳐보니
**권한과 무관하게 오늘부터 오는 칸이 따로 있었다.** 평범한 "필드"는 인사이트 "지표"와 다른 문이다.
```
total_views_count=52  shares_count=0  reposts_count  total_like_count  total_comments_count
copyright_check_information={"status":"complete","matches_found":false}   ← 원본성(§7.1)
boost_eligibility_info={"eligible_to_boost":true}  media_audio_type  is_shared_to_feed
```
`metrics.py note()` 주석에 내가 **"API는 이것들 대부분을 줄 수 없다"**고 써놨다. 필드 하나 거리였다.
§14 게시물 화면 · §15 인사이트 안쪽 · §16 에러 메시지 · **§17 독스의 다른 절** — 네 번 같은 병.

- **손입력 대조 통과:** `shares_count` **3/3 정확 일치**, `total_views_count` 13/13에서 손입력
  이상(스냅샷 이후 증가분만큼). → 손입력을 자동으로 갈아끼웠다. `saved_count`는 늘 `None`
  (소유자 전용) → **저장만 인사이트 권한 전용으로 남는다.**
- **원장이 즉시 커졌다:** 조회 있는 게시물 **14 → 83**, 공유 **3 → 83**, 저작권 결과 0 → 7.
- **§6 비용 결정이 처음으로 통제된 데이터 위에 섰다.** 기간을 09-19 이후로 고정한 세그먼트별
  조회 중앙값 = 266/312/314/322/261 — **평평하다.** E-0c·E-0d 유지가 n=3이 아니라 **n=32** 위에.
  §14.7의 "짧은 릴에 불리한 신호"는 폐기.
- **반증:** 보고서의 주제별 표는 거의 전부 **날짜**다. 주제가 블록 발행이라 평안(중앙일 09-11,
  조회 90)·담대(09-16, 120)가 정확히 제재 기간이고 월별 중앙값은 8월 289 · **9월 170** · 10월 317.
  **"주제가 공유를 만든다"는 지지되지 않는다.** 주제 효과를 알려면 **교차 배치**가 필요하다(G-3.9).

**코드:** **`ig_catalog.py` 신규** — 공식 레퍼런스 전사가 요청의 단일 출처(묶음·단건·계정 행이
전부 파생, 손으로 적는 변경 금지). 조건부 실패 지표는 `bundle: False`로 격리하고 묶음은
`media_product_type`별로 만든다. **`ig_probe.py` 신규** — 전 항목을 하나씩 쳐보고
`api_support.json`에 판정을 남기며 **❌가 "없다"의 증거가 아니라고 스스로 경고**한다;
`--if-stale`로 25일마다 자동 재측정. **`insights.py`** — 필드 23개 전수(+`node`), **계정 인사이트
신규 차원 → `account.json`**(`reach|follow_type` = 비팔로워 도달 직접), 거부는 `errors`에 기록,
목록 전체를 죽이는 `copyright_check_information`은 분리. **출처 표시 명시화**(`_api`/`_field`/
`_manual`) — 추론했던 첫 구현이 골로새서 3:14 좋아요를 **2에 동결**시켰다(API는 4).
**`save_ledger.sh`의 조용한 유실 경로 제거** — `git add`에 없는 파일이 섞이면 전체가 실패하고
`nothing to commit`으로 끝나 **metrics.json까지 저장되지 않았다.**
`RULES.md` G-3 1~10 · `check_rules.py` 11개 · `test_catalog.py` 44개(역테스트 5종 확인).

**원석님 1회 작업은 §16 그대로 유효**(권한 승인 → `reach`·`saved`·`reels_skip_rate`·계정 전체).
그 전에도 위 7칸은 매일 자동으로 쌓인다.

## 2026-10-07 — **삭제가 매번 되살아나고 있었다** (디모데전서 2:4)

원석님이 `DeIOmzNkYbd`(디모데전서 2:4, 10-06)를 내리겠다고 하셔서 원장을 보다가,
**C4b가 약속한 것의 절반만 돌아가고 있었다**는 걸 확인했다. 지난번 고린도전서 15:55을
**손으로** 지워야 했던 것이 바로 그 증거였는데 그때 알아채지 못했다.

- **① 측정값을 통째로 버렸다** → `metrics_deleted.json`으로 **옮긴다**. 내려간 게시물도
  조회·공유·`veo_seconds`를 측정한 건이고 E-0c·E-0d가 그 칸 위에 서 있다. **보관 못 하면
  지우지도 않는다.**
- **② 그 삭제가 병합에서 살아남지 못했다.** `save_ledger.sh`는 `origin/main`으로 리셋 후
  합집합 → prune이 뺀 행을 원격이 매번 돌려준다. **경합이 아니라 정상 경로**
  (`merge({a},{a,deleted})→{a,deleted}` 시뮬레이션 확인). `ledger_merge` 독스가 가리키는
  패턴 그대로: **추가만 되는 권위 파일 + 읽을 때마다 버리기**(`metrics.load()`).
- **③ 구절이 풀리지 않았다.** `used_verses`는 추가만 된다 → 해제를 **매 실행 보관 파일에서
  재계산**(병합이 되돌려도 수렴). 살아 있는 원장 행 **과** 살아 있는 캡션 둘 다 보고,
  어느 한쪽이라도 쓰면 안 푼다(같은 구절 2회 게시 중 1건만 삭제).

**가로선은 진짜였다 — 그리고 46건 중 1건뿐이다.** 게시된 영상을 받아 프레임으로 확인:
`has_ruled_line → RULED(411px에서 97% 열이 끊김)`. **계정에 남은 릴 46건을 전수로** 같은
게이트에 돌린 결과 **ruled 1/46, 오탐 0/45**, 2등이 42% — 한계 55%는 **42~97% 빈 구간**에
있다. `has_seam`은 통과시킨다(17x<30x): 톤이 아니라 직선이 문제라 별도 게이트가 필요했던
것이 수치로 남았다. 원자료 `notes/deleted/ruled_line_sweep_20261007.json`.
⚠️ 그 쓸기의 `clearance` 칸은 **게시된 프레임 값이라 `CLEARANCE_MIN`과 비교 금지** — 그게
이 게이트를 2주간 멀게 한 바로 그 실수다.

`RULES.md` C4c·C4d·C4e · `check_rules.py` 8개 · `test_prune.py` **27개**(역테스트 5종 확인).
**남은 것: 원석님이 앱에서 삭제** → 03:20 KST `insights.yml`이 보관·구절 해제까지 자동.
삭제 직전 API 스냅샷은 `notes/deleted/18632946685003547.json`에 이미 떠놨다(조회 322).

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

## 2026-10-31 — **Google이 Veo를 치웠다. 15개 릴이 조용히 정지 이미지로 나갔다** (STRATEGY.md §18)

원석님이 "영상이 안 올라오네, 다 이미지로 가는거야?"라고 물어서 확인했더니 맞았다 — 그런데
설정을 바꾼 적이 없었다. **2026-10-23 05:18 KST부터 구글이 예고 없이
`veo-3.1-fast-generate-preview`를 API에서 치웠다.** 직접 호출로 받은 에러:
`models/veo-3.1-fast-generate-preview is no longer available`. 이 키로 받는 모델 **60개 중
영상 생성(`predictLongRunning`)을 지원하는 게 하나도 없다** — 구글이 권한 대안으로 제시한
`gemini-omni-1.1-flash`도 `generateContent`만 지원해 영상과 무관하다. 매 호출이 즉시 404로
실패해 기존 폴백(정지+줌)으로 떨어졌고, **`watch.py`는 이 종류의 실패를 전혀 보지 않아서**
2026-10-30까지 **15개 릴이 연속으로** 움직임 없이 나가는 동안 아무 경보도 없었다
(`metrics.json`의 `segments=0, veo_seconds=8.0`이 10-23 이후 예외 없이 반복).

**대안은 이미 가지고 있던 자격증명 안에 있었다.** 정지 이미지에 쓰던 Higgsfield 계정
(`HF_API_KEY`/`HF_API_SECRET`, `fetch_higgsfield.py`)이 Wan 2.7 image-to-video도 제공한다
(`api.higgsfield.ai/wan/v2.7/image-to-video`) — **새 자격증명이 필요 없었다.** `fetch_veo.py`를
이 엔드포인트로 교체했다. 함수 시그니처(`animate(still_png, dest, ...)`)와 모듈 상수
(`MOTION`/`CALMER`/`CONTINUE`/`CALLS`/`SECONDS_PER_CALL`)는 그대로라 `daily_post.py`는 한 줄도
안 바꿨다. **실제 자격증명으로 실제 호출해서 검증했다**(`output/_bg.png` 입력): 8.03초,
720x1280(9:16 자동 유지, aspect 파라미터 없음), 카메라 고정, 0·4·7초 프레임을 직접 비교해 구도
유지 확인, `make_video.motion_score`로 재니 overall 1.50(목표 1.5에 근접) — 기존 Veo 프롬프트
문구가 그대로 통한다.

비용은 초당 $0.05 견적(구독 할인 미적용, ₩1,333/$ 환율) ≈ **₩66.65/초 — 옛 Veo ₩138.33/초의
절반 이하.** `metrics.VEO_WON_PER_SECOND`를 갱신했고 **아직 청구서가 아니라 견적**이라고
주석에 명시했다(실제 Higgsfield 청구서가 오면 재보정 필요). `test_veo_budget.py`는 이제 이
상수를 중복 하드코딩하지 않고 `metrics.py`에서 직접 가져온다 — 공급자가 또 바뀌어도 두 파일이
따로 썩을 수 없게. 재계산한 월 최악 비용 ₩95,976(기존 ₩199,192의 절반 이하). `RULES.md` E-0
개정, `check_rules.py`·`test_veo_budget.py` 전부 통과(E0/E0c/E0d/E3 포함), `verify.sh`의 다른
실패 2건(`test_catalog.py`, `test_linebreak_tiers.py`)은 이 변경과 무관한 기존 결함으로
확인했다(스태시 후 재현).

**남은 것 — 이름 부채:** `fetch_veo.py`라는 파일명/모듈명이 더 이상 사실과 다르다(Veo를 안
쓴다). 최소 변경으로 빨리 고치려고 리네임은 하지 않았다 — `daily_post.py`·`check_rules.py`·
`test_chuseok.py` 세 곳이 `fetch_veo.`를 참조한다. 리네임은 기계적이라 다음 세션에 해도 된다.
**`watch.py`에 "Veo 연속 실패/폴백" 경보가 아직 없다** — 이번처럼 8일을 조용히 흘려보내지 않을
유일한 방법인데 아직 손대지 않았다.

## 2026-11-01 — 이름 부채 정리: `fetch_higgsfield.py`→`fetch_image.py`, `fetch_veo.py`→`fetch_motion.py`

10-31 로그에 적어둔 "남은 것"을 처리했다. 두 파일 다 **공급자 이름이 아니라 역할 이름**으로
바꿨다 — `fetch_higgsfield.py`는 실제로는 **Gemini**로 이미지를 생성하고(기본 `MODEL = "gemini"`,
`gemini-3-pro-image`), Higgsfield는 한 번도 안 쓰이는 폴백 경로(`soul`/`flux`)로만 남아 있었다.
반대로 `fetch_veo.py`는 10-23 이후 **Higgsfield** Wan 2.7로 모션을 만드는데 이름은 옛 공급자
Google Veo를 가리키고 있었다. 둘 다 "무엇을 하는지"로 바꿔 혼동의 뿌리를 없앴다
(원석님이 "Higgsfield도 쓰나, Gemini만 쓰는 줄 알았다"고 물은 게 바로 이 이름 때문이었다).

함수·상수 이름은 전부 그대로다(`generate_background`, `animate`, `MOTION`/`CALMER`/`CALLS` 등) —
바뀐 건 **파일명과 import 문뿐**이다. `daily_post.py`·`check_rules.py`·`test_chuseok.py`·
`gate_probe.py`·`test_seam.py`·`reflection.py`·`make_examples.py`·`fetch_lyria.py`·
`test_ruled_line.py`·`test_clearance.py`·`content_law.py`·`audit_refs.py`·`metrics.py`
13곳 전부 기계적으로 치환, `RULES.md`·`CONTENT_RULE.md`의 모듈 참조도 같이 갱신했다.
**날짜 있는 과거 로그(`notes/*.md`, 이 파일의 지난 항목들)는 안 건드렸다** — 그 당시 실제
파일명이 그거였으니 역사 기록으로 맞다. `verify.sh` 전부 통과 확인 후 커밋.

## 2026-11-01 밤 — `test_catalog.py`가 "곧 다시 깨질" 모양으로 고쳐져 있었다

원석님이 "fix"라고만 쓰셔서, 전 턴에서 "무관한 기존 결함"이라고만 적어뒀던 `test_catalog.py`
실패를 실제로 고쳤다. 원인은 날짜 하드코딩 — `MEDIA`와 세 군데 `run_backfill()` 호출이 전부
`"published": "2026-10-06T20:00:00+0000"`를 썼는데, `insights.backfill()`은 `_is_young()`으로
**`metrics.MATURE_DAYS`(14일) 안의 글만** 도달(`reach`) 같은 과금 엔드포인트를 부른다. 이 테스트가
쓰인 10-07에는 "오늘"이었던 그 날짜가, 오늘(11-01) 기준 26일 전이라 **엔드포인트 호출 자체가
건너뛰어졌다** — "엔드포인트가 평문 필드를 이긴다"는 검증 세 줄이 **검증하려던 코드 경로를 한
번도 타지 않고** 실패한 것이었다. 테스트가 깨진 이유와 테스트가 말하는 이유가 달랐다.

고친 법: 하드코딩된 날짜를 지우고 `_YOUNG = datetime.now(timezone.utc) - timedelta(days=1)`로
교체 — `test_prune.py`가 이미 쓰던 양식이다(`now - timedelta(days=N)`). 이러면 테스트가 **언제
돌려도** "어제 올라온 글"을 기술하므로 다시는 날짜 때문에 저절로 안 깨진다. `verify.sh` 전체
재확인, 통과.

**찾은 교훈:** 지난 턴에 "pre-existing, unrelated"라고 적은 것 자체는 사실이었다(내가 만든 결함이
아니었다) — 하지만 "unrelated니까 안 고쳐도 된다"로 끝낸 게 틀렸다. 날짜 하드코딩은 **시간이
지나면 반드시 다시 터지는 종류**라, 발견한 자리에서 고치지 않으면 다음에 또 "원인 불명 테스트
실패"로 재발한다.

## 2026-11-04 — 그리드가 "방·바다·들판 반복"으로 보인 이유 + 레퍼런스 스터디 봇 (STRATEGY.md로는 안 남김, RULES.md D-1/D-2)

원석님이 실제 그리드 스크린샷을 보고 그대로 짚었다: "같은구조의 방 바다 들판 좀 따분한거같은데."
`pick_scene()`의 no-repeat 원장은 **정확히 설계대로** 작동하고 있었다 — 지난 2건과 같은
**카테고리 키**만 피한다. 문제는 70개 카테고리 중 `sea`·`shore`·`harbor`·`reflection_lake`·
`river`·`waterfall`·`rain_pond`·`still_water` 여덟 개가 전부 "넓은 물 위에 열린 하늘"로 **똑같이
보인다**는 것 — 카테고리는 안 겹쳐도 사람 눈에 보이는 **구조**는 세 번 연속 겹칠 수 있었다.
(09월의 "다 무슨 방에서 우울한 벽만" 수정은 실내/실외 **비율**만 손봤지, 실외 안에서의 구조
쏠림은 건드린 적이 없었다.)

**고친 것:** `fetch_image.SCENE_STRUCTURE`가 70개 카테고리를 7개 구조 버킷(room·water·
sky_mountain·field·forest·landmark·still_life)으로 묶고, `pick_scene(avoid_structure=4)`가
최근 4건과 같은 버킷을 **추가로** 피한다. 실측(동일 시작점 60회 연속 pick_scene): 구조 제약
없이 인접 버킷 반복 **4회** → 기본값으로 **0회**. `test_scene_structure.py`가 역테스트로
(`avoid_structure=0`에서는 반드시 반복이 생김을 먼저 확인한 뒤) 이 수치를 고정한다.

**추가로 만든 것 — 2주마다 외부(@dailymayim)와 비교하는 `reference_study.py`.** D-1이 고친 건
우리 자신과의 쏠림뿐이라, 바깥 기준이 없으면 70개 카테고리 전부가 다시 좁은 방향으로 같이
드리프트해도 아무도 모른다. `.github/workflows/reference-study.yml`(1일·15일)이 `business_discovery`
API를 먼저 시도하고 — **2026-11-04 기준 막혀 있음 확인**(`(#10) Application does not have
permission for this action`, 발행에 쓰는 바로 그 토큰인데도) — 막히면 텔레그램으로 그리드
스크린샷을 요청한다. **이 스크립트는 fetch_image.py를 절대 고치지 않는다**(check_rules.py가
강제) — 보고서만 후보를 제시하고 실제 추가는 검토된 코드 변경이다.

**바로 첫 스터디를 실제로 돌렸다**(API가 막혀 있으니 이번 대화에 원석님이 보내주신 그리드
스크린샷 2장·24타일을 직접 판독 — `notes/reference-study/2026-11-04.md`). 결과: 레퍼런스는
sky_mountain(25%)·room·forest·water가 고르게 섞여 있는데 우리 최근 로테이션은 still_life(정물
클로즈업)가 28%로 쏠려 있었다. 그리고 우리 70개 카테고리 어디에도 없는 모티프 5개 —
**불꽃놀이·주택 외관·피아노 있는 실내·옥상 전망·달이 보이는 하늘** — 를 후보로 남겼다(다음
세션이 검토 후 추가할지 결정).

**버그 하나를 그 자리에서 잡았다:** `record_run()`이 커스텀 `ledger=` 딕셔너리를 받아도
**항상 진짜 `reference_study.json`에 저장**하고 있었다 — `test_reference_study.py`가
`verify.sh`에서 처음 돌자마자 방금 만든 진짜 스터디 결과를 테스트 더미 데이터로 덮어썼다(같은 날
발견). `load_ledger`/`save_ledger`/`record_run`에 `path=` 를 꿰어 테스트는 임시 파일을 쓰게
고치고, "record_run이 명시적 경로를 줬는데도 진짜 파일을 건드리면 잡히는" 역테스트를 추가했다.
이 저장소가 원장 유실(08-26, 09-22)마다 반복해 온 바로 그 실수의 작은 재현이었다.

`RULES.md` D-1·D-2, `check_rules.py` 7개, `test_scene_structure.py` 8개·`test_reference_study.py`
28개(역테스트 다수 포함), `verify.sh` 전체 통과 확인 후 커밋.

## 2026-11-08 — D-1이 배포되자마자 병합이 조용히 되돌리고 있었다: `scene_i`가 4주째 얼어 있었다

원석님이 그리드 스크린샷을 보내며 또 짚었다: "같은구조의 방 바다 들판 좀 따분한거같은데 ...
레퍼런스 스터디 멈추지않고 루프 돌리면서 다양화 하는 시스템 추가해두라고 했잖아." 먼저 확인한 것 —
화면의 모든 타일에 ▶ 아이콘이 있다(사진이 아니라 릴이 맞다), 로컬 저장소가 origin보다 30 커밋
뒤처져 있어서 **최신 production 데이터로 다시 받아 확인**했다.

**찾은 것: D-1(구조 버킷 회피, 11-04 배포)이 배포된 지 하루 만에 사실상 멈춰 있었다.** 원인은
새 코드가 아니라 `save_ledger.sh`가 쓰는 `ledger_merge.py`의 일반 규칙 — "counters take max() /
list는 합집합" — 이 `state.json`의 두 필드와 충돌한 것이었다. 2026-10-13~11-08 production 커밋
40개를 전수로 읽어 확인:
```
scene_i             전부 정확히 140 (== len(SCENES))  — 4주 내내 단 한 번도 안 바뀜
used_scene_cats 꼬리  전부 동일한 마지막 10개 항목       — 4주 내내 단 한 번도 안 바뀜
post_i              216 → 326                        — 정상적으로 계속 올라감 (대조군)
```
- `scene_i`는 `pick_scene()`이 `len(SCENES)`를 법으로 도는 **회전** 인덱스지, 끝없이 증가하는
  카운터가 아니다. 한 바퀴를 돌아 작은 값으로 내려가는 순간 `max(ours, theirs)`가 예전의 더 큰
  값을 영원히 붙잡는다 — 회전이 천장(140)에 한 번이라도 닿으면 그 자리에서 고정된다.
- `used_scene_cats`는 `daily_post.py`가 `del scene_cats[:-4]`로 직접 자르는 "최근 4개" 창이지
  "지금까지 쓴 것의 집합"이 아니다. 리스트 병합은 **값으로** 중복 제거하는데, 카테고리는 70개뿐이고
  게시는 300건을 넘었으니 오늘 새로 고른 카테고리는 거의 항상 원격 사본 어딘가에 이미 있다 — 그래서
  조용히 "이미 있음"으로 버려진다. 이 파일 자신의 docstring이 경고하는 "삭제를 표현할 수 없다" 함정과
  정확히 같은 모양인데, 아무도 이 원장을 그 경고의 대상으로 인식하지 못했다.
- 결과: `pick_scene`이 매번 거의 같은 지점에서 검색을 시작해 거의 같은 "최근 목록"과 비교했다 —
  **D-1의 회피 로직 자체는 옳았는데, 비교 대상이 4주째 똑같았다.** "방 세 번, 등대 두 번"은 바로 이
  증상이다.

**고친 것:** `ledger_merge.OURS_REPLACES_KEYS = {"scene_i", "used_scene_cats"}` — 이 두 키만
병합에서 로컬이 방금 쓴 값을 그대로 쓴다. `post_i`·`music_i`·`used_verses`·`used_clips`·
`used_photos`는 역테스트로 **그대로 `max()`/합집합임을 확인**했다 — 이 파일이 원래 막으려던
사고(08-26/08-29 중복 게시)를 다시 열면 안 되므로. `state.json`은 손으로 고치지 않았다 — 다음
실행 한 번이면 로컬이 계산한 새 값이 그대로 저장되어 자가 치유된다.

**"루프 돌리면서 다양화"에 대한 답:** 비교하니 요청하신 것과 가장 가까운 결손은 새 기능이 아니라
바로 이 블라인드 스팟이었다 — D-1이 이미 "다양화 시스템"이었는데 인프라가 그걸 조용히 꺼뒀다.
그래서 루프를 새로 만드는 대신 `watch.py`에 **상시 감시**를 붙였다: 매 실행(하루 6회)마다
`(scene_i, used_scene_cats 꼬리)` 지문을 이전 실행과 비교해, `SCENE_FREEZE_H`(30시간) 이상 안
바뀌면 한 번 알린다. 이번 사고를 ~4주가 아니라 하루 반 안에 잡아낼 수 있었던 장치다. D-2(2주마다
@dailymayim과 비교)는 그대로 유지 — 다음 주기는 11-18.

`RULES.md` D-3, `check_rules.py` 3개, `test_ledger_merge.py` 11개(역테스트 포함: scene_i를
OURS_REPLACES_KEYS에서 빼면 실패함을 직접 확인) · `test_slot_media.py`에
`SceneRotationFreezeIsAnnounced` 6개 추가. `verify.sh` 전체 통과 확인 후 커밋.

## 2026-11-08 — 11/8 아침 사진 대체: Higgsfield 크레딧 소진. 그리고 Higgsfield는 **버리기로 했던 업체였다**

원석님이 11/8 아침 게시물(잠언 23:18)이 영상 없이 사진으로 나간 걸 물어서, 실제 CI 로그를
`gh run view --log`로 열어 원인을 직접 확인했다(추측 아님):
```
20:03:05  veo motion failed (not_enough_credits) → background-zoom still
```
Higgsfield 계정의 **크레딧이 바닥났다는 게 API 응답 그대로**다. 전 세션(10-31)이 "충전하면
해결된다"고 한 건 맞았다.

그런데 원석님이 이어서 지적한 게 더 큰 문제였다 — **"힉스필드 버리고 구글 쓰기로 했었잖아"**.
저장소를 뒤져보니 그 결정은 어디에도 적혀있지 않았다(대화에서만 있었고 글로 남지 않음 —
durability 원칙이 경고하는 바로 그 사고). 그리고 그 결정은 **이미지 쪽에서는 지켜지고 있었다**
(`fetch_image.py`는 기본값이 Gemini, Higgsfield는 한 번도 안 쓰이는 폴백) — 원석님이 기억하는
"써보니 큰 차이 없어서 구글로" 결정은 이미지 얘기였고 거기선 맞게 돌아가고 있다.

문제는 **영상(모션)** 쪽이다. 10/23에 구글이 체험판 Veo 키를 끊었을 때, 전 세션이 임시방편으로
"이미 계정이 있다"는 이유로 **이미지 테스트용으로 만들어뒀던 그 Higgsfield 계정**을 영상
생성으로 돌렸다(10-31 로그). 그 순간 "이 업체는 버린다"는 결정이 조용히 뒤집혔는데, 아무도
그걸 결정이라고 인식하지 못했다 — 그냥 "자격증명이 이미 있으니 재사용"으로 보였다. 오늘
크레딧이 떨어진 게 그 뒤집힌 결정의 첫 청구서다.

**아직 결정 안 됨 — 다음 세션/원석님이 정할 것:**
1. 그대로 Higgsfield 충전해서 쓰기 (제일 빠름, 그런데 원석님이 이중결제·오버스펙·비싸다고 느낀
   바로 그 업체를 계속 쓰는 것)
2. 영상도 구글 정식 유료 Veo로 옮기기 (원래 의도에 맞음, 단 구글 클라우드 계정·결제 연결이라는
   새 설정이 필요하고 10-31 조사로는 더 비쌀 수 있음)
3. 제3의 업체 검토

**작업 전 확인할 것:** Higgsfield 계정 자체(이메일·결제 상태)는 이 저장소에 기록이 없다 —
원석님만 그 계정 로그인 정보를 안다. 이 세션엔 브라우저 도구가 없어 직접 확인 못 했다.

## 2026-11-09 — 10-31의 "Omni는 영상을 못 만든다"는 틀렸다: 다른 문이 있었다 (옵션 2 재오픈)

원석님이 "결제 끊긴 거 아니지 않냐"고 캐물어서 `fetch_motion.py`의 404를 라이브로 다시 확인하는
중(§ 바로 위 대화), 구글이 대안으로 제시한다던 `gemini-omni-1.1-flash`를 **10-31에 썼던 것과
같은 방식**(`generateContent`)으로 다시 쳐봤더니 같은 에러가 나왔다: `"This model only supports
Interactions API."` — 10-31 로그와 `fetch_motion.py` 주석이 "Omni는 `generateContent`만 지원해서
영상과 무관하다"고 적어둔 바로 그 결론의 **근거가 된 테스트 자체가 틀린 문을 두드린 것**이었다.
웹 검색으로 찾은 `POST /v1beta/interactions` 라는 **별도 엔드포인트**로 같은 키·같은 계정에 실제
호출해 확인했다(추측 아님, mp4 바이트를 직접 받아 ffmpeg로 열어봤다):

```
gemini-omni-1.2-flash (2026-11-05 GA, 10-31 조사 시점엔 존재하지도 않았던 버전)
  이미지→영상 실제 성공: 8.04s, 720x1280(9:16 명시 가능 — response_format.aspect_ratio="9:16")
  정물(밀밭+팻말+가방, 글씨 포함) 0s/5s/9.5s 프레임 비교 — 카메라·구도·글씨 전부 고정, 왜곡 없음
  길이는 자연어로 제어됨("exactly 8 seconds" → 8.04s), duration_seconds 파라미터는 없음(400 reject)
  오디오가 자동으로 같이 나옴(AAC 스테레오) — 우리는 Lyria로 음악을 따로 입히므로 ffmpeg -an으로
  버리면 그만, 막는 필드는 없음(부정 프롬프트로 조절 권장, 문서 표기)
```
**가격 — 실측과 문서가 맞아떨어졌다.** 720p는 초당 5,792 토큰 × $12/백만 토큰 ≈ **$0.07/s**
(360p $0.023/s · 1080p $0.104/s). 실제 호출 토큰 사용량(57,920 토큰 / 10.03s, 15,448 토큰 / 8.04s)이
이 요율과 거의 정확히 일치했다. **새 자격증명 필요 없음 — 지금 이미지 생성에 쓰는 바로 그
`GEMINI_API_KEY`**. 즉 10-31/11-08 로그가 "영상도 정식 Veo로 가려면 구글 클라우드 결제 계정을
새로 연결해야 한다"고 적어둔 건 **Vertex AI 경유 얘기였고, Interactions API 경유는 해당 없다** —
지금 쓰는 키로 바로 된다.

**비용 비교 (추정, 현재 Higgsfield 실측 ₩59,718/월 대비):**
```
Gemini Omni 1.2 Flash  $0.07/s(720p) → Higgsfield $0.05/s의 1.4배 → 월 ≈ ₩84,000 (추정)
월 한도(RULES.md E-0b) ₩260,000 — 이 추정으로도 32% 수준, 한도 안에 넉넉히 들어온다
```
오늘 검증 호출(이미지→영상 2건 + 텍스트→영상 2건, 720p/360p 섞음)로 실제 과금 발생 —
대략 **$1.5~2 (₩2,000~2,700)** 수준으로 추정(청구서 미확인, 견적).

**아직 결정 안 됨 — 이건 "결론"이 아니라 "옵션 2가 생각보다 쉽다"는 발견이다.** 코드는 아직
한 줄도 안 바꿨다(`fetch_motion.py`는 여전히 Higgsfield). 바꾸려면: ① `fetch_motion.animate()`를
Interactions API 호출로 교체(엔드포인트·요청 구조가 Veo/Higgsfield 둘과도 다름 — 롱러닝 폴링이
아니라 동기 호출, 응답이 base64 비디오를 직접 담고 있음) ② 받은 mp4에서 `-an`으로 오디오 제거
③ `metrics.VEO_WON_PER_SECOND`를 $0.07/s 기준으로 갱신(아직 견적, 청구서 아님 — Higgsfield 때와
같은 경고를 그대로 달아야 함) ④ `RULES.md` E-0/E-0b, `test_veo_budget.py`, `check_rules.py` 재확인.
**원석님이 "바꿔"라고 하면 다음 세션이 이 순서대로 하면 된다** — 지금은 보고만 하고 멈췄다.

## 2026-11-09 밤 — 바꿨다: `fetch_motion.py`가 Higgsfield에서 Gemini Omni로 넘어갔다, 실전 검증까지

원석님 지시: "바꿔 당장 힉스는 결제도 안하고 있어 ... 코드도 신중하게짜 qa, 엔드투엔드테스트,
결과물 검수, 코드 검수하는 에이전트 따로 만들어." 바로 위 §(11-09 아침)가 "옵션 2가 생각보다
쉽다"는 발견이었던 것을 실제 전환까지 끝냈다. 코드를 쓰기 전에 **문서부터 의심했다** — 웹 검색
결과 3곳(Google 공식 문서 포함)이 서로 다른 요청 스키마를 보여줬고, 그중 한 곳은 `duration`을
`"10s"` 같은 문자열 필드로 설명했는데(다른 공급자/제품 문서와 섞여 있었을 가능성), 실제 계정에
라이브로 쳐보지 않고는 어느 쪽도 믿지 않기로 했다.

**실제로 9번 과금해서 확인했다** (7회 원시 프로토콜 탐색 + `animate()` 실전 2세그먼트 체인 1회):
- **동기 호출**이다 — Veo·Higgsfield처럼 제출 후 폴링하는 게 아니라, HTTP 응답 자체에
  `status:"completed"`와 완성된 클립이 바로 담겨 있다. 코드가 훨씬 단순해졌다.
- 매번 8.0~8.04초/720x1280, `response_format.aspect_ratio`로 화면비 **직접 지정 가능**
  (Wan 2.7엔 없던 필드).
- 클립마다 AAC 오디오가 자동으로 붙고 끌 방법이 없어 ffmpeg `-an`으로 **제거**(Lyria 음악과
  겹치면 묵음이 아니라 제거해야 이음매 클릭음을 막는다).
- 전용 negative-prompt 필드가 없어 금지 목록을 프롬프트 본문에 "피할 것"으로 접어 넣었다
  (정지 이미지의 Gemini 호출이 이미 그렇게 하고 있던 방식 그대로 — 공급자가 같아지니 패턴도
  하나로 합쳐졌다).
- **`urllib.request`가 ~4.5MB 응답을 3번 중 1번 중간에 끊었다**(`IncompleteRead`, 끝에서 약
  20KB 모자라게). `requests` 라이브러리는 3/3 성공. 생성과 과금은 어느 쪽이든 끝난 뒤였고
  클라이언트 쪽 다운로드만 달랐다 — 그래서 `fetch_motion.py`는 `requests`를 쓰고,
  `import fetch_motion`만으로는 무거워지지 않도록 함수 안에서 지연 임포트했다
  (`check_rules.py`가 정확히 이 이유로 `import fetch_motion`만 한다).

**전체 파이프라인 실전 실행까지 했다** — `daily_post.py --now --emit`(원격 origin/main으로
원장 동기화 후, 끝나고 정확히 그 상태로 복원, 발행 직전에서 멈춤). 결과: 에베소서 6:23,
이미지 게이트 통과, 모션 2세그먼트 시도(오프닝 2회 재시도 후 "가장 덜 나쁜 것" 채택 — 책
책장에 "글씨로 보일 수 있는 자국"이 있다고 비전 게이트가 매번 거부, **이건 기존 LAW 검사가
제대로 작동한 것이지 새 공급자의 결함이 아니다**), 연결 세그먼트는 검사 탈락으로 1세그먼트만
출고, `veo_calls=3`·`veo_seconds=24.0`·`segments=1`로 `_meta.json`에 정확히 기록됨. 최종 릴
프레임을 직접 열어 확인 — 사람 없음, 글씨 없음, 텍스트 가독성 정상, 오디오는 Lyria 음악만
남아 있음(모델 자체 오디오 제거 확인). 드라이런이 쓴 `state.json`/`metrics.json`은 전부
원래 상태로 복원했다 — 실제 운영 원장은 건드리지 않았다.

**비용 재계산, 숫자로.** `metrics.VEO_WON_PER_SECOND`를 실측 2건(각 46,336 토큰/8.04초 ≈
초당 5,762토큰 ≈ $0.069)과 공식 $0.07/s 단가가 거의 일치해 $0.07/s로 갱신(₩1,333/\$ 기준
≈ ₩93.31 — 아직 견적, 청구서 아님). `test_veo_budget.py`가 자동으로 이 상수를 다시 읽어
재계산: 최악의 경우 월 ₩134,366 — Veo 예산 ₩200,000의 67%, 전과 같은 여유. `verify.sh`
전체(테스트 25개 + 규칙 감사) 통과 확인.

**코드 검수.** `code-review` 스킬(high)로 별도 패스를 돌려 `fetch_motion.py`·`metrics.py`·
`RULES.md`·`.github/workflows/daily-post.yml` diff를 검토시켰고, 실제로 결함 3개를 잡았다
(전부 `_strip_audio` 한 함수에 몰려 있었다):
1. `base64.b64decode()`가 잘린/깨진 응답에서 실패하면 `<dest>.raw.mp4` 임시 파일이
   `try/finally` 범위 **밖**에서 만들어져 디스크에 남는다(게시마다 최대 3회 호출되는 경로라
   드문 일이 아니라 매일 벌어질 수 있는 누수).
2. `subprocess.run(..., capture_output=True)`가 ffmpeg의 stderr를 **버려서** 실패해도
   "non-zero exit status"만 남고 원인이 안 보인다 — 바로 이 저장소가 "15개 릴이 조용히
   나간" 사고에서 배운 "조용한 실패가 비싸다"는 교훈과 같은 모양.
3. **더 근본적으로, `_strip_audio` 자체가 불필요했다** — `make_video.chain_clips()`는
   `-map "[v]" -an`로, `build_reel_native()`는 `-map "[v]" -map "2:a"`(2번 입력 = Lyria
   음악)로 **이미 명시적 스트림 선택**을 하고 있어서, `fetch_motion.py`가 내보내는 클립에
   모델 자체 오디오가 있든 없든 최종 릴에는 Lyria만 남는다. 직접 확인: 오디오가 있는
   원본 응답을 그대로 `build_reel_native()`에 넣어봤더니 출력엔 193kbps AAC 스트림
   **하나만** 남았고 그게 Lyria 트랙이었다(모델 쪽 원본과 비트레이트가 다름).

세 결함 모두 `_strip_audio` 함수와 중간 임시 파일을 **통째로 제거**하는 것으로 한 번에
해결됐다 — 디코딩한 바이트를 바로 `dest`에 쓴다. ffmpeg 서브프로세스 1회·임시 파일 1개가
클립마다 사라졌고, `import subprocess`/`import make_video`도 더 쓸 데가 없어 제거했다.
수정 후 `verify.sh` 전체 재확인, 통과.

**남은 것.** `fetch_image.py`의 Higgsfield Soul 폴백(정지 이미지, 드물게만 쓰임)은 이번
범위 밖 — 원석님 불만은 구체적으로 **영상/모션** 비용이었고, `HF_API_KEY`/`HF_API_SECRET`는
그쪽 때문에 당분간 계속 필요하다. Higgsfield 계정 자체를 완전히 끊을지는 별도 결정.

## 2026-11-09 — "크론 꺼지는거 보는거까지" 감시 인프라 — 만들자마자 살아 있는 사고를 하나 잡았다

원석님 지시: *"모든걸 감시 감독 검수 qa 하는 인프라를만들어 크론 꺼지는거 보는거까지."*
GitHub Actions의 실제 실행 기록을 전수로 당겨보는 데 30분이 안 걸렸고, **지금 당장 살아
있는, 아무도 모르는 실패를 하나 찾았다** — 자세한 경위·수치는
`notes/cron-health-2026-11-09.md`, 새 규칙은 `RULES.md` **I절**.

**찾은 것:** `weekly-carousel.yml`의 가장 최근 스케줄 실행(2026-11-08)이 슬라이드는 만들고
**발행만 조용히 실패**해 있었다 — `urllib.error.HTTPError: HTTP Error 400`. 아무 데도 알림이
안 갔다. 원인은 `post_instagram._post()`가 `_get()`과 달리 **HTTPError의 응답 본문을 한
번도 풀어본 적이 없었다는 것**(RULES.md H0, `_get`만 2026-10-07에 고쳐지고 `_post`는 한 달
넘게 같은 구멍이었다) — Meta가 보낸 실제 이유가 그대로 버려졌다. **고쳤다** — `_open()`
하나로 합쳐서 `_get`·`_post` 둘 다 같은 길을 쓴다.

**새로 만든 것 — `cron_health.py`.** 다른 모든 감시는 **결과**(게시됐는지, 좋아요가
괜찮은지)를 보는데, 이건 **그 결과를 만드는 크론 자체**가 살아 있는지를 GitHub의 실행
기록에 직접 물어서 본다. 한계값은 **cron 식이 아니라 실측**에서 나왔다 —
`comment-reply.yml`이 "10분마다"로 설정돼 있지만 86일·1000건 실측 중앙값은 48분, 최악
12.3시간이었다(GitHub이 분당 미만 크론을 심하게 지연시키는 게 확인됨). 설정값을 그대로
한계로 썼으면 매일 오탐이 났을 것이다. `watch.py`(하루 6회)가 이걸 호출하고, 사람이 할 일은
**아직 하나 남았다** — GitHub 전체가 죽는 경우(이 감시도 같이 죽는 유일한 사각지대)를 잡을
외부 데드맨 스위치(healthchecks.io, 무료) 가입. 절차는 그 노트 §3.

**다섯 개의 독립 코드 검수 에이전트(`code-review` 스킬, high)를 돌렸고, 그중 세 개가 같은
심각한 버그를 서로 다른 각도에서 잡았다:** `evaluate()`가 워크플로 파일의
`created_at`/`updated_at`을 **무조건** 기준선에 포함시키고 있어서, 죽은 크론을 그냥 둔 채
**그 워크플로 파일을 아무 이유로든 수정만 해도** `updated_at`이 갱신되며 정지 시계가
조용히 0으로 리셋됐다 — 하필 "가장 중요하다"고 라벨 붙인 `refresh-token.yml`에서 가장
위험한 모양으로. `last_run`이 있으면 **항상 그것만** 기준으로 쓰도록 고쳤고,
`test_cron_health.py`에 역테스트로 고정했다. 그 외에 고친 것: ① `ok is None`("판정
불가")이 매번 조용히 버려지던 것 → 전부 `None`이면(=GITHUB_TOKEN 권한이 깨진 것 같은
전체 장애) 그 자체로 즉시 1건 알리게 함. ② `watch.py`가 `findings()`를 실행당 두 번
불러 GitHub API를 두 배로 때리고, 그 사이 일시적 API 흔들림이 생기면 쿨다운이 조기에
풀릴 수 있던 것 → 프로세스당 1회로 캐싱. ③ `WATCHLIST`가 손으로 적은 고정 목록이라
"워크플로 #6을 깜빡하면" 아무도 모르는 구조였던 것 → `check_rules.py`가 이제
`.github/workflows/*.yml`을 직접 스캔해서 `schedule:` 있는 워크플로 전부가 WATCHLIST에
있거나 `DELIBERATELY_UNWATCHED`에 이유와 함께 적혀 있는지 강제한다(`daily-post.yml`은
watch.py의 기존 슬롯-누락 감시가 더 나은 오라클이라 제외, `watch.yml`은 자기 자신이라
제외 — RULES.md I-2). ④ `check_rules.py`의 H0 검사가 `_get`/`_post`라는 **이름**만 보던
것 → 파일 전체에서 `urlopen(` 호출이 `_open` 안에만 있는지 세어서 미래의 `_delete()` 같은
새 함수도 커버. 나머지 몇 개(공급자 간 HTTP-에러-해석 로직이 4벌로 흩어져 있는 것 등)는
위험 대비 이득이 낮아 이번엔 손대지 않고 적어만 둔다.

`RULES.md` I-1·I-2, `check_rules.py` 11개(+ H0 보강 1개), `test_cron_health.py` 29개(역테스트
다수), `verify.sh` 전체 통과 확인 후 커밋.

**남은 것 — 지난주 캐러셀을 다시 올릴지는 콘텐츠 판단이라 손대지 않았다.** 요일이 지났고
RULES.md C의 중복/타이밍 규칙에 걸릴 수 있어 원석님 확인 필요. 그리고 위 ③의
HEALTHCHECK_URL 가입이 유일하게 남은 사람 몫이다.

## 2026-11-09 늦밤 — "감독을 한곳에서 해, 여기저기 뿌리지 말고": `control_center.py`

바로 위 cron_health 작업까지 포함해 세어보니 "감독"이라는 이름 아래 이미 다섯 개의 서로
다른 명령이 있었다 — `watch.py`(운영 알림), `check_rules.py`(코드가 규칙과 맞는지),
`ig_doctor.py`(토큰 권한), `ig_probe.py`(그 권한 지도가 최신인지), `reference_study.py`
(외부 비교가 기한인지). 다섯 이름을 전부 기억하고 전부 돌려야 전체 그림이 나왔다.

**실제로 찾은 구멍 하나:** `checks.yml`(푸시마다 도는 verify.sh)이 실패하면 **GitHub Actions
화면에만** 남았다. 운영 알림 채널(watch.py → 텔레그램)과 정적 검증 계층이 한 번도 서로
말을 섞은 적이 없어서, 코드가 며칠째 깨져 있어도 아무도 몰랐을 수 있다 — 바로 이 레포가
반복해서 걸려 넘어진 "조용한 실패" 패턴을 한 단계 위에서 재현하고 있었다.

**만든 것 — 다섯 개를 다시 짜지 않고 하나로 모았다.**
```
python3 control_center.py            # 보고서 출력
python3 control_center.py --notify    # 같은 보고서를 텔레그램으로 한 통
```
각 섹션은 기존 함수를 그대로 부른다 — `watch.findings()`(운영+크론, 이미 통합돼 있던 것),
GitHub API로 `checks.yml` 최신 실행 결과(이전엔 알림 경로가 전혀 없던 구멍), `ig_doctor`의
`describe()`/`NEEDED`로 토큰 권한(비싼 지표별 프로브는 안 부름 — 자주 돌려도 안전해야
"한곳에서 보기"가 습관이 된다), `ig_probe.is_stale()`·`reference_study.due()`로 진단
최신성. **처음 돌려보자마자 실제 문제를 하나 띄웠다** — 최근 게시 3건(11/8 05:04·20:49,
11/9 05:09)이 연속으로 움직임 없이 나갔다. 조사해보니 새 사고가 아니라 이미 로그에 있는
그 사고(Higgsfield 크레딧 소진, 11/9 16:10 Gemini Omni로 전환)의 흔적이었다 — 전환 커밋이
오늘 아침 게시(05:09) **이후에** 들어갔다. 오늘 저녁 슬롯부터는 저절로 풀려야 한다.

**`checks.yml`에 실패 알림 연결.** `if: failure()`로 watch.py와 같은 텔레그램 채널에
핑한다. 처음엔 YAML 폴딩된 `python3 -c "..."` 한 줄로 썼다가 — 폴딩 규칙과 `${{ }}` 치환이
뒤섞여 `-c` 문자열 맨 앞에 공백이 남으면서 `IndentationError`가 나는 걸 **실제로 실행해서**
잡았다(실패할 그날에야 들켰을 버그). GitHub이 이미 주는 환경변수
(`GITHUB_REPOSITORY`/`SHA`/`SERVER_URL`/`RUN_ID`)를 읽는 작은 파일 `notify_ci_failure.py`로
바꿔서 `${{ }}` 치환 자체를 없앴다.

**되돌릴 뻔한 사고 하나.** 역테스트로 "`check_rules.py`의 새 검사가 진짜 조작을 잡는지"
확인하려고 `/tmp`에 백업하고 `control_center.py`를 임시로 깨뜸 — `/tmp` 쓰기가 샌드박스에
막혀 백업이 조용히 실패했는데 그걸 못 보고 원본에 손상이 그대로 남았다. 바로 다음 명령에서
디스크 변경 알림으로 발견하고 즉시 복구, `git diff`로 깨끗한지 재확인했다. **이 레포가 왜
"백업 후 복구"를 원장마다 강제하는지**를 몸으로 다시 겪었다 — 백업 자체도 성공을 확인해야
한다.

`RULES.md` J-1·J-2, `check_rules.py` 5개(각각 특정 호출 문자열을 찾아 "파일이 있다"가 아니라
"그 호출이 실제로 쓰인다"를 검사 — I-1이 이미 쓴 같은 패턴), `test_control_center.py` 25개
(watch/cron_health/ig_doctor/ig_probe/reference_study 전부 몽키패치, 네트워크 호출 없음),
`verify.sh` 전체 재확인 후 커밋·푸시.

**남은 것:** control_center는 지금 순수 온디맨드다(사람이나 내가 필요할 때 돌림) — watch.py의
"평소엔 조용히" 철학과 충돌하지 않게, 별도 주기적 알림은 추가하지 않았다. 필요해지면
`--notify`를 watch.yml 같은 크론에 얹는 건 나중 결정.

## 2026-11-09 밤 2 — 원석님이 "실패 메일이 끝없이 온다"고 물어서 **CI가 19일째 빨간불이었던 걸 찾았다**

`control_center.py`를 막 만든 지 한 시간도 안 돼서, 바로 그게 고치려던 종류의 사고가 하나 더
있었다. `gh run list --workflow=checks.yml`로 전수 확인: **2026-10-20부터 11-09까지 19일,
커밋 15개 내내 `checks.yml`이 단 한 번도 통과하지 못했다.** `checks.yml`에 실패 알림(J-2)이
오늘 밤에야 붙었으니 그 전엔 GitHub Actions 화면에만 남았고, 그 사이 세션들의 "verify.sh
통과 확인"은 전부 **로컬 macOS 기준**이었다 — CI(Ubuntu)에서는 계속 떨어지고 있었다.

**원인을 끝까지 쫓았다.** `verify.sh`의 `step()`이 실패 로그를 `grep -E "FAIL|Error|assert" |
head -8`로 잘라내서, CI 화면에는 정작 숫자가 안 보였다. 버리는 `debug/test-tracking-ci`
브랜치를 만들어 실제 ubuntu-latest 러너에서 직접 측정해 보니:
```
Pillow 13.0.0, FreeType 2.14.3 (CI)  —  나눔명조 한글 20,927자 전수가 정확히 41.8125px
RULES.md F-4-A가 적은 값                —  42.00px (2026-10-19, 로컬 macOS에서 한 번 측정)
차이 -0.1875px = -12/64px — 노이즈가 아니라 힌팅 방식 차이로 생기는 깨끗한 고정 오프셋
```
`test_tracking.py`가 이 **macOS 전용 값을 하드코딩**해 놓고 모든 플랫폼에 그걸로 단언하고
있었다 — 그 규칙이 적힌 **그 커밋부터** CI에서 떨어졌다(최초 실행부터 바로 실패).

**다행히 게시물은 한 번도 잘못 나간 적이 없다.** `generate.text_w`/`draw_text`는 42.0을
참조한 적이 없고 늘 `font.getlength()`로 그 자리에서 측정한다 — 깨진 건 테스트와
RULES.md의 **적어놓은 숫자**뿐이었다. 이 파일 자신의 docstring이 이미 "COL_W는 generate.py에
물어본다, 다시 적지 않는다"는 원칙을 세워뒀는데, 바로 그 옆 클래스가 그 원칙을 어겼다.

**고친 것:** `test_tracking.WidthIsComputableNotJustMeasurable`이 HANGUL/SPACE를
`setUpClass`에서 **그 플랫폼의 실제 렌더러로** 측정한다(하드코딩 제거) — 어느 플랫폼에서
돌든 "재는 쪽과 그리는 쪽이 같은 숫자를 읽는다"는 이 파일의 실제 목적을 검증한다.
`check_rules.py`에 재발 방지 검사 추가(하드코딩 복귀를 정규식으로 잡음, 역테스트로 실제
옛 형태를 잡는지 확인). RULES.md F-4-A에 정정 각주 — 42.00/710/734/21~22자는 macOS
측정값이고 운영 서버 실측(41.81px)과 다르다고 명시, 방향은 안전(더 좁게 그려져 여유가
늘어남)하다고 적었다. 수정 커밋을 메인에 푸시한 뒤 **실제 CI가 2026-10-15 이후 처음으로
성공**하는 것까지 직접 지켜봤다(`42598198827`).

**스크린샷에 같이 있던 네 번째 종류의 메일**(`.github/workflows/watch.yml - main: No jobs
were run`)은 별개다 — 코드 결함이 아니라 GitHub 자체의 동작이다: schedule/workflow_dispatch
전용 워크플로 파일을 수정해 푸시하면, 그 커밋이 `push` 트리거와 안 맞아 "실행된 잡 없음"이라는
알림이 뜬다. watch.yml을 고친 11-09 저녁 커밋(`53b58b4`)이 바로 그 경우였다. 고칠 코드가 없다.

**원석님께 남은 선택:** 이제 CI 실패는 Telegram으로도 온다(J-2) — GitHub 메일(각 워크플로
실행마다 "구독 중"으로 따라오는 알림)과 중복이다. GitHub 계정 설정 → Notifications →
Actions에서 끄시면 텔레그램 채널 하나로 합쳐진다(코드가 아니라 원석님 개인 GitHub 설정이라
제가 대신 못 바꾼다).

`RULES.md` F-4-A 정정, `check_rules.py` 1개 신규(역테스트 확인), `test_tracking.py` 수정,
`verify.sh` 전체 통과, 실제 CI green 확인 후 커밋·푸시(`067f44c`).

## 2026-11-09 밤 3 — 끝없는 실패 메일의 진짜 원인: `watch.py` 자신(알림 시스템)이 꺼져 있었다

19일짜리 CI 적신호를 고친 지 몇 시간 뒤, 원석님이 또 "실패 메일이 끝없이 온다"는 스크린샷을
보냈다. 타임스탬프를 맞춰보니 두 다발이 섞여 있었다 — ①~17:40 KST까지의 「Checks: All jobs
have failed」는 **이미 고친 그 19일 적신호의 꼬리**(F-4-A 수정이 10:04 UTC에야 머지됐다)였고,
②~17:40 KST **이후**의 「watch.yml workflow run」 실패는 **그날 밤 처음 보는 새 사고**였다.

`gh run list --workflow=watch.yml`로 전수 확인하니 **그날 08:40 UTC(`53b58b4`, "feat(I): cron
liveness watchdog") 커밋 이후 모든 push가** watch.yml에 대해 **0개 잡(job)짜리 실패 런**을
만들고 있었다 — 그 전 커밋들은 전혀 안 그랬다. `gh workflow run watch.yml -f test=true`로
직접 디스패치해서 원인을 확정했다: `422 Unrecognized named-value: 'secrets'`. 그 커밋이 새로
넣은 **Heartbeat 스텝의 `if: ${{ secrets.HEALTHCHECK_URL != '' }}`** — `secrets` 컨텍스트는
`if:` 조건식 안에서 직접 못 읽는다는 GitHub Actions 고유 제약을 어겼다. 이게 **파일 전체의
파싱을 깨뜨려서**, push뿐 아니라 **그날의 크론(스케줄) 실행도 똑같이 깨졌을 것**이라는 뜻이다 —
즉 "뭔가 조용히 죽으면 알려야 할" 바로 그 감시 시스템이, 만들어진 지 몇 시간 만에 스스로 조용히
죽어 있었다.

**고친 법:** `secrets.HEALTHCHECK_URL`을 `env:`로 한 번 거쳐서 `if: ${{ env.HEALTHCHECK_URL
!= '' }}`로 읽게 바꿨다(공식 우회 패턴). `check_rules.py`의 I-2 검사가 하필 **깨진 그 문자열
그대로**(`"secrets.HEALTHCHECK_URL != ''"`)를 찾고 있어서 이 버그를 전혀 잡지 못했었다 —
고친 모양(`env.HEALTHCHECK_URL != ''`)을 고정하도록 같이 수정, 옛 형태로 되돌리면 다시 잡힌다.
**로컬 통과만 믿지 않고 실제로 검증했다:** 수정 커밋(`3d2c392`) 푸시 후 ① 같은 커밋에 대해
더 이상 push 실패 런이 생기지 않음, ② `workflow_dispatch --test`가 `422` 없이 성공, ③ 그 실행
로그에 `telegram: sent` · `test alert sent`가 실제로 찍힌 것까지 확인했다.

**곁다리로 본 것 — 새 문제 아님:** 같은 시각 `pages-build-deployment`(GitHub Pages, `/docs`
246MB 미리보기 사이트, 레포 고유 기능) 런 하나가 "Timeout reached, aborting!"로 실패했다 —
앞뒤 모든 런(초 단위 수십 건)은 전부 성공이라 **일회성 인프라 지연**으로 판단, 코드 변경 없음.
`control_center.py`가 "최근 3건 연속 움직임 없이 나갔다"고 한 건은 이미 있는 경보 경로가
작동한 것(11-09 낮 Higgsfield→Gemini Omni 전환 직후 구간과 겹침) — 별도 조치 없이 기존
watch.py 3연속 경보에 맡긴다.

`check_rules.py` I-2 수정(역테스트: 옛 깨진 형태로 되돌리면 실패 확인), `verify.sh` 전체 통과,
실제 GitHub에서 디스패치·텔레그램 수신까지 확인 후 커밋·푸시(`3d2c392`).

## 2026-11-10 — **인사이트 토큰 발급 끝났다.** `ig_doctor.py`가 자기 검증 방식을 잘못 짚고 있던 것도 고쳤다

10-07부터 세 세션째 "사람만 할 수 있는 1회 작업"으로 남아있던 `IG_INSIGHTS_TOKEN` 발급을
이번에 끝까지 밟았다 — `ycbc0501` 개발자 등록 → Instagram 제품의 `bible-IG` 앱에 인사이트
권한 추가 → @saintseoul_studio 테스터 수락 → **0절 확인(활성 계정이 @saintseoul_studio인지
먼저 확인)** 후 OAuth 승인 → 코드 교환 → 60일 토큰. 경위는
[notes/insights-token-2026-10-07.md](notes/insights-token-2026-10-07.md) §7.

그런데 받은 토큰을 `ig_doctor.py`로 확인하니 ❌가 나왔다 — **토큰은 정상인데 진단 스크립트가
잘못 짚고 있었다.** 원인 둘: ① `debug_token`을 발행 토큰과 같은 앱(`META_APP_ID`)으로 쳤는데
`IG_INSIGHTS_TOKEN`은 **다른 앱**(`IG_APP_ID`, Instagram Login 쪽)에서 발급돼 앱이 안 맞아
거부됐다. ② 맞는 앱으로 바꿔 쳐도 여전히 거부됐다 — **Instagram Login 토큰은 `debug_token`
계열 엔드포인트 어디로도 scope를 조회할 수 없다**(두 엔드포인트·여러 필드로 직접 확인). 이
저장소가 두 달째 "권한 없음"으로 오독했던 그 `(#10)` 에러가, 이번엔 **토큰 종류 자체의
한계**였다. 유일한 증거는 교환 시점에 한 번 찍히는 `granted:` 출력뿐.

**고친 것:** `ig_doctor.py`가 `debug_token`이 막히면 실제 지표 호출(`reach`·`views`·
`shares`·`reels_skip_rate`·`ig_reels_avg_watch_time`) 성공 여부로 판정한다 — 추측 대신 보이는
결과로 판정한다는 이 파일 자신의 원칙 그대로. 수정 후 실측 확인: `reach=167`·`views=184`·
`shares=0`·`reels_skip_rate=83.8`·`ig_reels_avg_watch_time=2356` 전부 성공.
`gh secret set IG_INSIGHTS_TOKEN` 완료. `insights.py`는 이미 이 토큰 종류(`graph.instagram.com`
+ `me`)를 알고 있어서 **코드 변경 없이** 다음 `insights.yml` 실행(03:20 KST)부터 `reach`·
`saved`·`reels_skip_rate` 등을 자동 수집한다. `verify.sh` 29개 테스트 전부 통과 확인 후 커밋.

**남은 것:** 다음 `insights.yml` 실행 후 실제로 `reach`/`saved`가 채워졌는지 한 번 더 확인.

## 2026-11-10 — 그 "한 번 더 확인"이 진짜 사고를 두 개 더 찾았다: 토큰은 멀쩡했고, 그 다음 두 겹이 깨져 있었다

원석님이 "확인해"라고만 보내서, 바로 위에 적힌 "남은 것"을 실제로 밟았다. 어제(11-09) 끝낸
`IG_INSIGHTS_TOKEN`을 `ig_doctor.py`로 다시 쳐보니 **멀쩍이 성공**이었다(`reach=163`·
`views=188`·`shares=4`·`reels_skip_rate=85.5` 전부 ✅) — 토큰 자체는 전혀 문제가 아니었다.
문제는 그 토큰이 **처음으로 이겨서 쓰이기 시작한 순간** 드러난, 한 번도 실행된 적 없던
두 코드 경로였다. `gh run list --workflow=insights.yml`로 전수 확인하니 오늘 03:34 KST
스케줄 실행이 **실패**했다(`42736744636`) — 로그를 끝까지 읽어 원인 둘을 확정했다.

**① `recent_media()`가 `graph.facebook.com`을 하드코딩하고 있었다.** `insights.api()`는
`IG_INSIGHTS_TOKEN`이 있으면 이제 그걸 쓰고, 그 토큰은 `graph.instagram.com` + 계정 경로
`"me"`에서만 유효하다(G-2 1-d가 이미 적어둔 규칙). 그런데 `metrics.prune_deleted()`가
그 토큰·경로를 들고 `post_instagram.recent_media()`를 불렀을 때, 이 함수는 `base`를
받지 않고 **무조건 `graph.facebook.com`에** 물었다 — 그 호스트에서 Instagram-Login
토큰은 `(190) Cannot parse access token`으로 거부된다. 이 에러는 `prune_deleted`의
`except`에 걸려 **"prune skipped"로만 찍히고 끝났다** — 이건 "지울 게 없다"와 글자
모양이 같아서, 삭제된 게시물이 구절을 1년 동안 묶어두는 바로 그 사고(RULES.md
C4c/C4d/C4e, 10-07에 한 번 고쳤던 것)가 **다른 입구로 재발할 뻔했다.**

**② `account()`의 마지막 출력 줄이 응답 모양을 하나만 가정했다.** `reach|follow_type`은
보통 쪼갠 딕셔너리로 오는데, 오늘 응답은 **쪼갤 게 없어 맨 숫자**를 돌려줬다. `r.items()`가
`AttributeError`로 죽으면서 **스크립트 전체가 중단**됐다 — `account.json`은 그 직전에
이미 저장됐지만, 뒤에 와야 할 `solo_fields()`·`followers()`·`metrics.report()`는 그날
한 번도 안 돌았다(오늘자 팔로워 곡선 한 점이 비었다).

**③ 그리고 ①·②가 겹쳐서 세 번째 손실을 만들었다.** `insights.yml`의 "Save the ledgers"
단계에 daily-post.yml의 "Save no-repeat ledger"가 쓰는 `if: always()`가 없었다 —
그래서 ②가 크래시하자 이미 디스크에 쓴 `backfill()`/`account()` 결과가 **커밋 한 번
못 하고 러너와 함께 사라질 뻔했다.** 지금은 다음 실행이 같은 날을 다시 쓰므로 실손실은
없었지만, 패턴은 08-26 원장 유실과 같다 — 앞 단계가 무엇으로 실패하든 이번 실행이
이미 만든 진행분은 저장해야 한다.

**고친 것:** `post_instagram.recent_media()`가 `base` 인자를 받고(기본값은 기존과 동일하게
`graph.facebook.com`), `metrics.prune_deleted()`와 `insights.py __main__`이 그걸 끝까지
들고 간다. `account()`의 출력 줄은 `isinstance(r, dict)`로 먼저 확인한다.
`insights.yml`의 "Save the ledgers"에 `if: always()`를 붙였다. 새 테스트
`test_insights_domain.py`(recent_media의 기본/명시 호스트, 스칼라 응답이 안 죽는다는 것
— 실제로 라이브 응답과 같은 모양으로 재현해 확인)와 `test_prune.py`에 `base`가 끝까지
전달되는지 보는 역테스트 추가. `check_rules.py` G2.1e·G2.1f·G2.1g 6개 신설.
`verify.sh` 전체 재확인.

## 2026-11-10 — "보내고 끝내지 말고 끝까지 확인해": 오늘 발행 확인 + 멈춰 있던 `(190)` 조사를 끝까지 밟음

원석님 지시: "앞으로 이거 나한테 보내고 끝이 아니라 문제 확인하고 다시 업로드할수있게 다시
검수해. 오늘거 그래서 올라갓는지까지 확인해." 직전 세션이 "`IG_INSIGHTS_TOKEN`이 `(190)
Error validating application`으로 안 먹는다 — 제가 확인하겠습니다"라고만 쓰고 멈춘 채
세션이 끝났다. 이번에 둘 다 실제로 끝까지 했다.

**① 오늘 발행 — 실제로 확인.** GitHub Actions 로그에서 모닝 슬롯이 220분 지연 후 실제로
올라간 것을 찾았고(`media id → 18211787989370988`), 그 미디어를 Graph API로 직접 쳐서
**지금도 살아 있는 것**까지 확인했다 — `https://www.instagram.com/reel/DfiitTkisKP/`,
`timestamp 2026-11-09T23:45:53Z`(=08:45:53 KST). "워크플로가 success"와 "실제로 인스타에
떠 있다"는 이 레포가 위클리 캐러셀 사고(11-09)에서 이미 다르다고 배운 것이라 코드 성공만
보고 끝내지 않았다.

**② `(190)` 에러 — 조사해보니 문제가 아니었다. 그런데 그 질문을 쫓다가 진짜 버그를 찾았다.**
`ig_doctor.py`를 다시 돌려보니 토큰은 멀쩍이 정상이었다(`reach=167·views=189·shares=4·
reels_skip_rate=84.9%` 전부 ✅) — `(190)`은 이미 11-09 밤에 적어둔 그 구조적 한계
(`debug_token`이 Instagram Login 토큰을 원천적으로 못 읽음) 그대로였고, `ig_doctor.main()`은
이미 실제 호출로 우회해 올바르게 ✅를 낸다. 그런데 **`control_center.py`는 아니었다.**
`token_section()`이 `ig_doctor.describe()`/`NEEDED`를 **따로 다시** 읽고 있었고, 거기엔 그
우회 로직이 없어서 **매번 "인사이트 권한 없음"을 오보**하고 있었다 — 토큰이 완전히
정상인데도, 영원히. `control_center.py`를 "한곳에서 보라"고 만든 바로 다음 날(11-09)부터
이미 거짓 경보 하나가 들어 있었던 셈이다.

**고친 것:** `ig_doctor.py`의 `main()` 안에 있던 "`debug_token` 실패 시 실제 지표 호출로
판정" 로직을 `verdict()` 함수로 뽑아냈다 — 입력은 평범한 환경변수 이름
(`IG_ACCESS_TOKEN`/`IG_INSIGHTS_TOKEN`), 출력은 `ok_tokens`/`errors`/`probe_lines`.
`main()`과 `control_center.token_section()` 둘 다 이제 **이 하나만** 부른다. 비용은 원래
취지대로 유지됨 — 실제 지표 호출은 `debug_token`이 그 토큰을 못 읽을 때만 돈다(지금처럼
`IG_INSIGHTS_TOKEN`이 Instagram Login일 때뿐이고, Facebook Login 토큰은 여전히 호출 1번).

`RULES.md` J-1 갱신, `check_rules.py`의 기존 검사("`ig_doctor.describe(` + `NEEDED`가
`control_center.py`에 있는지")를 **반대로** 뒤집었다(`verdict(`은 있고 `describe(`은 없어야
통과) — 옛 검사 그대로 두면 이 고침 자체가 "재사용 아님"으로 잡혔을 것이다. 되돌림 검증:
옛 패턴 문자열로 새 조건을 수동 평가해 실제로 거짓임을 확인. `test_control_center.py`에
역테스트 2개 추가 — ①`debug_token` 실패 + 실제 호출 성공 → `ok True`(이 버그의 재현),
②`debug_token` 실패 + 실제 호출도 실패 → `ok False`(가짜 성공 방지). `verify.sh` 전체
(테스트 29개 + 규칙 검사) 재확인 후 커밋.

**덤으로 — `control_center.py`가 오늘 새로 잡은 진짜 경보 둘은 둘 다 이미 알던 사고의
꼬리였다.** 지표 백필의 "최근 스케줄 실행 실패"는 G-2.1e/f/g 고침(오늘 오전) **이전**
실행이고 다음 스케줄(내일 03:20 KST)이 지나면 자동으로 풀린다. 주간 캐러셀의 "최근 스케줄
실행 실패"는 11-09에 고친 H0 버그(그 캐러셀이 바로 그 사고의 증거)이고, 지난 주 캐러셀을
다시 올릴지는 이미 11-09 로그에 "콘텐츠 판단, 원석님 확인 필요"로 적어둔 채 남아 있다 —
새로 만든 결정이 아니라 기존 결정을 다시 확인한 것이다.

## 2026-11-10 — "크론잡 하나만 둬": 5크론 체인/대기/지터를 통째로 없앴다

원석님 지시: "복잡한 스케쥴러니 슬립이니 뭐 다 없애고 '그냥 시간되면 올린다' 이거 크론잡
하나만 둬." 지금까지 `daily-post.yml`은 슬롯마다(05:00/19:00 KST) **1시간 간격 크론 5개를
체인**으로 걸고, `daily_post.wait_until_target()`이 깃허브 지연을 흡수하려고 ±10분 지터로
목표 시각까지 **잠들었다가** 깨서 "이 실행이 그 슬롯의 주인인가"를 창 계산으로 다퉜다. 이
체인은 2026-08-28 깃허브 크론이 최대 4~5시간씩 늦는 사고를 막으려고 만든 것이었는데, 그
뒤로 **스스로 버그를 두 달간 만들어냈다** — 같은 주장 창에 두 실행이 동시에 들어와 중복
게시(9/6, 데살로니가후서 2:17), "늦음"/"정시" 판정이 서로 다른 마감을 보고 아무도 주장하지
않아 게시가 통째로 빠짐(9/13, 9/14). 체인이 뭘 하든 **깃허브가 실제로 언제 실행하는지는
바뀌지 않는다** — 그 시각을 둘러싼 계산만 복잡해졌을 뿐이었다.

**지시 그대로 했다.** `.github/workflows/daily-post.yml`의 크론을 10개(5개×2슬롯)에서
**2개**(`"0 20 * * *"`=05:00 KST, `"0 10 * * *"`=19:00 KST)로 줄였다. `daily_post.py`에서
`wait_until_target()`·`CLAIM_WINDOW_MIN`·`LATE_LIMIT_MIN`을 통째로 삭제 — 더는 자지 않고,
`--jitter`도 사라졌다(쓸 지터가 없다). `main()`은 이제 `slot_already_filled(hour)` 한 줄만
본다 — "이 반나절에 이미 올라갔나"라는, 시각과 무관한 순수 중복 질문. `--now`는 그 중복
검사만 건너뛴다(빠진 게시물을 손으로 채울 때). `--catchup`도 지웠다(이미 체인 전용의
no-op이었다).

**남긴 것 — 전부 "스케줄링"이 아니라 "중복 방지"라서.** `slot_already_filled()`로 빌드 전
1번 + 게시 직전 재확인 1번, `concurrency` 그룹(이제 체인을 줄 세우는 게 아니라 수동 실행이
겹치는 경우에 대한 값싼 보험). 이 레포가 중복 게시로 도달이 6배 떨어진 적이 있어서(08-26),
API 호출 한 번짜리 안전장치까지 걷어내진 않았다 — "스케줄러·슬립을 없애라"는 지시와
"중복을 막는다"는 서로 다른 축이라고 판단했다.

**검증:** `check_rules.py`에 새 규칙 2개 — 크론이 슬롯당 정확히 1개인지, `wait_until_target`/
`CLAIM_WINDOW_MIN`/`time.sleep`이 `daily_post.py`에 다시 안 생기는지(체인이 조용히
돌아오는 것을 막는 역할). `--now`/`--hour`만 남은 인자 파서를 직접 실행해 `--help`에
`--jitter`·`--catchup`이 없는지, 중복 슬롯이면 `--now` 없이도 `_skip`이 바로 써지는지
확인(sleep 없이 즉시). `verify.sh` 전체(테스트 28개 + 규칙 검사) 통과, YAML 문법도
`pyyaml`로 직접 파싱 확인. `RULES.md` C2/C2b/C2c, `CONTENT_RULE.md` 1·10d 갱신.

**알려드릴 트레이드오프 하나:** `watch.py`의 "놓친 게시물" 경보(`GRACE_H = 2`시간)는 그대로
뒀다. 예전엔 체인의 첫 크론이 일찍 켜져서 깃허브 자체 지연은 어느 정도 가려졌는데, 이제
크론이 슬롯당 하나뿐이라 깃허브가 실제로 몇 시간 늦게 실행하면 — 게시는 결국 늦게라도
되지만 — `watch.py`가 그 사이에 "놓쳤다" 경보를 먼저 띄울 수 있다. 과거 기록상 깃허브가
일일 크론을 몇 시간씩 늦춘 사례가 있었던 만큼 가능성 있는 일이다. 원하시면 `GRACE_H`를
올리는 것도 검토할 수 있지만, 이번 지시(스케줄러/슬립 제거)의 범위 밖이라 손대지 않았다.

## 2026-11-10 — 바로 위 트레이드오프를 실측으로 다시 잡음: `GRACE_H` 2시간 → 1시간

원석님이 "2시간 늦으면 울립니다 > 너무 길지 않나 우리는 +-10분인가 기준으로 업로드하는데.
20분이면 충분하지 않나"라고 물었다. **±10분 전제가 틀렸다** — 그건 방금 없앤 옛 체인
(`wait_until_target`)의 **목표치**였을 뿐, 실측은 전혀 그렇게 나온 적이 없었다.

```
최근 발행 40건, 슬롯(05:00/19:00 KST) 대비 실제 지연
  중앙값 37분   p90 190분   최대 230분   >20분 52%   >60분 42%   >2시간 22%
```
가장 지연이 컸던 건들(11/9 저녁 230분, 11/10 아침 227분)을 실행 로그로 추적하니 **빌드 자체는
9~12분**이었다 — 150~230분짜리 지연은 **오늘 없앤 5크론 체인의 주장(claim) 버그**가 만든
것이었다(어떤 크론도 슬롯을 제때 못 주장하고 늦게 깨어난 크론이 뒤늦게 올림). 그 체인을 오늘
C2에서 없앴으니 이 크기의 지연은 재발하지 말아야 한다.

그런데 **20분은 그래도 너무 공격적이다.** 체인 버그와 무관한, **깃허브 자체의 크론 발동
지연**만 따로 실측했다(이 저장소 시간별 크론 100건, 자기 예정 시각 대비) — **중앙값 37분,
p90 55분.** 빌드 10분을 더하면 아무 버그 없이 "정상"으로 돌아도 총 지연이 40~70분대가 흔할
수 있다는 뜻이다. 20분으로 잡으면 새 단일 크론 설계에서도 거의 매일 "놓쳤다" 오보가 뜰
위험이 크다.

**실측 기반으로 1시간(GRACE_H=1)을 선택했다** — p90 발동지연(55분)+빌드(~10분)를 약간의
여유로 덮는다. 다만 단일 크론 설계는 오늘 오후(C2, `bc61b79`)에야 배포돼 **이 값을 정할 때
그 설계 자체의 실측은 0건**이었다 — 1주 돌려보고 재조정해야 한다. `AskUserQuestion`으로
90분/60분/20분/2시간 유지 중 고르게 했으나 응답이 없어, 실측 중앙값에 가장 맞는 60분(1시간)을
기본값으로 넣고 보고한다. `watch.py` GRACE_H 1, `check_rules.py`의 리터럴 검사 갱신,
`RULES.md` 슬롯 누락 조항에 근거 수치 추가. `verify.sh`(테스트 29개 + 규칙 감사) 전체 통과.

## 2026-11-10 — "하얀 방이 벽인 이미지가 계속 나온다": `room`과 `still_life`가 같은 "벽" 프롬프트를 공유하면서도 다른 버킷이었다 (RULES.md D-4)

원석님이 레퍼런스 스터디(D-2)를 직접 하다가 그리드를 보고 짚었다: "레퍼런스를 스터디하는데도
하얀 방이 벽인 이미지가 이렇게 계속 나오는건가.. 오늘 또 들어갔어. 프롬프트에 이게 엄청 많이
들어간게 분명해." 추측으로 답하지 않고 `git log`로 `state.json` 커밋 70개를 전수 복원해 실제
발행 카테고리 시퀀스를 재구성했다.

**짚은 게 정확했다 — 그리고 두 가지가 겹쳐 있었다.** ① D-3(11-08)가 고친 회전 멈춤 버그는
이전에 적은 것보다 더 심했다 — `mist_mountain`이 **10-20~11-07, 33건 연속** 고정돼 있었다
(요약이 아니라 전수 확인은 이번이 처음). 11-08 수정 이후로는 실제로 매번 다른 카테고리가
나온다. ② 그런데 회전이 다시 돌아도 "벽"은 반복될 수 있었다 — `INTERIOR_CATS`(28개 카테고리)
전부가 동일한 `INDOOR_TOP` 프롬프트를 받는다("a tall expanse of the room's own wall ...
evenly lit and either pale and bright or deep in shadow"). 그런데 `SCENE_STRUCTURE`는 이
28개를 `room`(5개: bedroom·lamp_room·window_light·desk·cathedral)과 `still_life`(23개:
tea_cup·candle·flowers_vase 등)로 **나눠서** 등록해뒀다 — D-1(11-04)이 고친 건 "바다 아홉
개가 다 바다로 보이는" 문제였는데, "방"과 "정물"이 같은 벽 프롬프트를 공유한다는 건 그때도
지금도 등록된 적이 없었다. `pick_scene`의 `avoid_structure`는 이 딕셔너리만 보므로 `tea_cup`
바로 다음에 `bedroom`을 고르는 게 전혀 막히지 않았다. 오늘 아침(08:46 KST, 누가복음 12:29)
실제로 `tea_cup`이 나왔고, 직전 스크린샷 그리드에는 `lamp_room`·`window_light`도 같이 있었다
— 전부 "평평한 벽 앞의 사물/가구"로 똑같이 읽힌다.

**고친 것:** `fetch_image.SCENE_STRUCTURE`에서 `INTERIOR_CATS` 28개 전부를 단일 `room`
버킷으로 합쳤다(`room` 버킷 == `INTERIOR_CATS`, 테스트로 고정). `still_life` 버킷은
`INTERIOR_CATS`에 없는 두 카테고리(`curtain`·`sparrow` — 벽이 아니라 열린 창/맨가지,
`OUTDOOR_TOP`을 받음)만 남는다. 다른 6개 버킷과 `INTERIOR_CATS` 정의 자체는 안 건드렸다.
`test_scene_structure.py`에 역테스트 2개 추가 — 옛 5+23 분리를 재현해 200회 중 인접 반복이
실제로 생김을 먼저 확인한 뒤, 고쳐진 단일 버킷에서는 200회 중 0회임을 고정. `check_rules.py`의
D-1 커버리지 검사는 버킷 이름을 합쳤을 뿐 키 집합은 그대로라 변경 없이 통과. `verify.sh`
전체(테스트 30개 + 규칙 감사) 통과 확인 후 커밋.

**영상이 "딱봐도 AI"라는 지적은 이번 범위 밖이다.** `fetch_motion.py`(Gemini Omni, 11-09
전환)의 모션 프롬프트는 이미 "locked camera, barely-there motion"과 morphing/warping/
flickering 금지어를 포함하고 있어서, 맹목적으로 프롬프트를 더 건드리는 건 근거 없는 추측이
된다. 로컬에 최근 생성물이 남아있지 않아(파이프라인이 CI 전용) 직접 눈으로 확인도 못 했다 —
구체적으로 어느 릴의 어느 구간이 부자연스러웠는지 알려주시면 그 한 건을 프레임 단위로 뜯어서
원인을 짚겠다.

Pipeline entry point: `daily_post.py` (orchestrator) → `fetch_image.py` (image + gates),
`fetch_motion.py` (motion), `fetch_lyria.py` (music), `make_video.py` (reel), `generate.py` (text),
`post_instagram.py` (publish — and it is the CLI, not `daily_post.py`, that actually
publishes in CI). No-repeat ledgers live in `state.json`; performance in `metrics.json`
(`metrics.py`, backfilled by `insights.py`); comment replies in `comments.json`.
