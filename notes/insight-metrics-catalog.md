# 인사이트 지표 전수 목록 — 독스에 있는 것 전부

작업 시작 2026-10-07. 원석님 지시: **"독스 읽고 받을 수 있는 데이터 이번에 싹 다 정기적으로
받아. 예외 두지 말고. 독스에 있는 거 다 받고 거기서 우리가 쓸 걸 정해."**

그동안의 순서가 거꾸로였다 — 쓸 것 같은 것만 골라 요청해서, §15가 1순위로 지목한
`reels_skip_rate`가 API에 있는데도 두 달간 빠져 있었다. 이 파일은 **공식 레퍼런스에서 긁은
전수 목록**이고, 코드는 이 목록을 출처로 삼는다.

## 진행 상태

- [ ] 1. 미디어 인사이트 레퍼런스 긁기
- [ ] 2. 계정(IG User) 인사이트 레퍼런스 긁기
- [ ] 3. breakdown / metric_type / period 파라미터
- [ ] 4. 미디어 필드(인사이트 아닌 것 — `media_product_type`, `like_count` 등)
- [ ] 5. 코드에 전수 반영
- [ ] 6. 정기 수집 경로 확인(워크플로)
- [ ] 7. 쓸 것 고르기 + RULES/테스트

## 원본 수집 (아래에 긁은 것을 그대로 붙인다)

---

## 1. 미디어 인사이트 — 공식 레퍼런스 전수 23개
출처: developers.facebook.com/documentation/instagram-platform/reference/instagram-media/insights

| 지표 | 적용 미디어 | 설명 | 제약 |
|---|---|---|---|
| comments | FEED, REELS | 댓글 수 | 오가닉만 |
| crossposted_views | REELS | IG+FB 합산 재생 | FB 공유 안 했으면 오류 |
| facebook_views | FEED, REELS, STORY | FB에서의 재생 | FB 공유 안 했으면 오류 |
| follows | **FEED, STORY** | 이 미디어로 생긴 팔로우 | **REELS 아님** |
| ig_reels_avg_watch_time | REELS | 평균 재생 시간 | |
| ig_reels_video_view_total_time | REELS | 총 재생 시간(리플레이 포함) | 개발 중 |
| impressions | FEED, STORY | 노출 | **2024-07-02 이후 미디어 폐기** |
| likes | FEED, REELS | 좋아요 | 오가닉만 |
| link_clicks | STORY | 링크 탭 | |
| navigation | STORY | 스토리 이동 | breakdown=story_navigation_action_type |
| profile_activity | FEED, STORY | 프로필 방문 후 행동 | breakdown=action_type |
| profile_visits | FEED, STORY | 프로필 방문 | **REELS 아님** |
| reach | FEED, REELS, STORY | 고유 시청자 | 추정값 |
| reels_skip_rate | REELS | **첫 3초 내 건너뛴 비율** | 추정·개발 중 |
| replies | STORY | 스토리 답장 | EU/일본 사용자 0 |
| reposts | FEED, REELS, STORY | 리포스트 − 삭제분 | |
| saved | FEED, REELS | 저장 | |
| shares | FEED, REELS, STORY | 공유 | |
| total_interactions | FEED, REELS, STORY | 좋아요+저장+댓글+공유 − 취소 | 개발 중 |
| views | FEED, REELS, STORY | 재생/표시 횟수 | 개발 중 |
| total_comments | FEED, REELS | 전 표면 합산(광고 포함) | **FB 로그인 전용** |
| total_likes | FEED, REELS | 전 표면 합산 | **FB 로그인 전용** |
| total_views | FEED, REELS, STORY | 전 표면 합산 | **FB 로그인 전용** |

period: day·week·days_28·month·lifetime·total_over_range (응답은 자동 lifetime 고정)

**→ REELS에 유효한 16개:** comments crossposted_views facebook_views
ig_reels_avg_watch_time ig_reels_video_view_total_time likes reach reels_skip_rate
reposts saved shares total_interactions views total_comments total_likes total_views

**→ 우리가 릴로만 올리므로 `follows`·`profile_visits`·`profile_activity`는 릴에서 못 받는다.**
그래서 §15의 「미디어 팔로우」는 손입력으로 남는 게 아니라 **계정 단위로 받는 게 맞다**(아래 §2).

## 2. 계정(IG User) 인사이트 — 두 달간 한 칸도 안 받은 차원
출처: developers.facebook.com/documentation/instagram-platform/api-reference/instagram-user/insights

| 지표 | period | metric_type | breakdown | 제약 |
|---|---|---|---|---|
| accounts_engaged | day | total_value | — | 추정 |
| comments | day | total_value | media_product_type | 개발 중 |
| likes | day | total_value | media_product_type | |
| saves | day | total_value | media_product_type | |
| shares | day | total_value | media_product_type | |
| reposts | day | total_value | — | |
| replies | day | total_value | — | |
| total_interactions | day | total_value | media_product_type | |
| **reach** | day | total_value, time_series | **media_product_type, follow_type** | 추정 |
| **views** | day | total_value | **follower_type, media_product_type** | 개발 중 |
| **follows_and_unfollows** | day | total_value | follow_type | 팔로워 <100이면 안 줌 |
| profile_links_taps | day | total_value | contact_button_type | |
| follower_demographics | lifetime | total_value | age, city, country, gender | <100이면 안 줌 |
| engaged_audience_demographics | lifetime | total_value | age, city, country, gender | 참여 <100이면 안 줌 |
| impressions | day | total_value | — | **v22.0 폐기, 2025-04-21 종료** |

breakdown 값: follow_type = FOLLOWER · NON_FOLLOWER · UNKNOWN
            media_product_type = AD · STORY · REEL · CAROUSEL_CONTAINER · POST
            contact_button_type = BOOK_NOW · CALL · DIRECTION · EMAIL · INSTANT_EXPERIENCE · TEXT · UNDEFINED
timeframe: this_week · this_month (last_14/30/90_days·prev_month는 v20.0+ 폐기)
한계: 데이터 최대 48시간 지연 · 데이터 없으면 0이 아니라 빈 응답 · 인구통계는 상위 45개만

**★ `reach` + `breakdown=follow_type` = 비팔로워 도달을 API가 직접 준다.**
§14·§15에서 「도달/팔로워 = 1.09x니까 비팔로워에게 간다」고 추론한 것이 추론일 필요가 없었다.

## 3. 미디어 노드 필드 — 인사이트가 아니라 공짜로 따라오는 것
출처: developers.facebook.com/docs/instagram-platform/reference/instagram-media

읽을 수 있는데 안 읽던 것:
- shares_count · saved_count · reposts_count · total_views_count · total_like_count
  · total_comments_count (FEED/REELS, FB 로그인 전용) ← **인사이트 권한 없이도 오는 값**
- media_product_type · media_type · media_audio_type(MUSIC/ORIGINAL_SOUND) · is_shared_to_feed
- **copyright_check_information.status** ← 저작권 검사 결과(§7.1 원본성과 직결)
- boost_eligibility_info ← 광고 적격성(계정 상태 신호)
- is_ai_generated · alt_text · is_comment_enabled · shortcode · thumbnail_url · owner

---

## 4. 실제 API 판정 — `python3 ig_probe.py` (2026-10-07, 게시 토큰 = Facebook 로그인)

전체 판정은 `api_support.json`. 요약:

```
media_fields      ✅ 22 / ❌ 0     ← 인사이트 권한 없이 전부 옴
media_metrics     ✅  0 / ❌ 20    ← 전부 (#10). 단, 권한 없으면 가짜 이름도 (#10)이므로
                                      이 ❌는 "없다"가 아니라 "이 토큰은 못 묻는다"
account_fields    ✅ 11 / ❌  1    ← shopping_product_tag_eligibility만 거부
account_insights  ✅  0 / ❌ 33    ← 같은 (#10)
```

### ★ 권한 없이 지금 오는 값 (두 달간 "API는 못 준다"고 적어둔 것들)
```
total_views_count = 52        ← 조회수
shares_count = 0              ← 공유
reposts_count = 0             ← 리포스트
total_like_count / total_comments_count
copyright_check_information = {"status":"complete","matches_found":false}   ← 원본성
boost_eligibility_info = {"eligible_to_boost": true}                        ← 계정 건강
media_audio_type = ORIGINAL_SOUND · is_shared_to_feed · is_ai_generated
```

### 손입력과 대조 (G-2.6이 요구하는 검증) — 14건
```
ref              api_views  hand   api_shares  hand
고린도전서 10:24        266   260M            1     1
요한삼서 1:2           470   465M            5     5
디모데전서 1:5          311   311M            0     0
마태복음 10:31         237   222M            0     -
…
views  api>=hand 13/13 (정확히 같은 건 1건 — 나머지는 그 뒤로 더 쌓인 것)
shares api==hand  3/3  정확 일치
```
→ **`shares_count`는 화면의 「보내기」와 같은 수. `total_views_count`는 화면의 「조회」와 같은 수
   (손입력은 며칠 전 스냅샷이라 API가 크다).** 손입력을 자동으로 바꿔도 된다.

### 여전히 인사이트 권한이 필요한 것
```
reach · saved · reels_skip_rate · ig_reels_avg_watch_time
ig_reels_video_view_total_time · total_interactions
+ 계정 인사이트 전부(reach|follow_type 포함)
```
`saved_count`는 독스상 소유자 전용인데 이 경로로는 늘 None → 저장은 인사이트 전용으로 남는다.

### 필드 원자성 함정이 목록 조회에도 있다
`fields=…,copyright_check_information` 을 `/media?limit=40` 에 넣으면
**`9005 Video content was not found`로 페이지 전체가 죽는다**(옛 게시물 하나 때문에). 필드를
하나씩 걸어 확인함 — 나머지 21개는 전부 일괄로 안전. → `MEDIA_FIELDS_SOLO`로 분리.

---

## 5. 그래서 우리가 쓸 것 — 원석님 지시의 뒷부분 ("거기서 우리가 쓸 걸 정해")

전수 수집은 `ig_catalog.py`가 담당한다. **아래는 수집한 것 중 무엇을 보고 결정하는가**다.
수집은 예외 없이 전부, 판단은 소수만. (수집을 줄이는 변경은 RULES.md G-3 위반)

### 1순위 — 지금 당장 자동으로 오고, 결정을 바꾸는 것
| 칸 | 출처 | 무엇을 결정하나 |
|---|---|---|
| `views` (total_views_count) | 필드 | 모든 비율의 분모. 제재/유통 상태 |
| `shares` (shares_count) | 필드 | **릴 랭킹 신호**(sends/reach). 말씀 카드의 성패 |
| `likes` `comments` | 필드 | 상대 비교용 참여도 |
| `reposts_count` | 필드 | 전달의 두 번째 형태 |
| `copyright_check_information` | 필드(개별) | 원본성 — §7.1을 화면 아니라 게시물별로 |
| `boost_eligibility_info` | 필드 | 계정 제재 상태의 조기 신호 |
| `segments`/`duration` × `views` | 원장 | **Veo 지출**(E-0c/E-0d) |

### 2순위 — 권한 승인 즉시 1순위로 올라오는 것
| 칸 | 왜 |
|---|---|
| `reach` | 조회가 아니라 **사람**. 모든 비율의 올바른 분모 |
| `reels_skip_rate` | §15의 유일한 "또래보다 나쁨". 첫 2초 설계의 판정 기준 |
| `ig_reels_avg_watch_time` | 같은 질문의 연속값 |
| `saved` | 필드로는 안 옴(소유자 전용). 재방문 의도 |
| `reach \| follow_type` (계정) | **비팔로워 도달을 직접.** 추론 폐기 |
| `follows_and_unfollows \| follow_type` (계정) | 릴에 `follows`가 없으므로 이쪽이 정답 |

### 수집은 하되 **지금은 판단에 쓰지 않는 것** (이유를 적어둔다)
- `crossposted_views` · `facebook_views` — Facebook에 공유하지 않으므로 항상 거부/0.
  **공유를 시작하면 즉시 의미가 생기므로 요청은 유지**한다.
- `total_views`/`total_likes`/`total_comments`(지표) — 광고를 돌리지 않으므로 평범한 필드와 같다.
- `follower_demographics` · `engaged_audience_demographics` — 하루 단위로는 안 움직인다.
  주 1회 보면 되고, 지금은 권한도 없다.
- `profile_links_taps` · `replies` — 프로필 버튼도 스토리도 쓰지 않는다. 0이 기준선이 된다.
- **주제별 표** — 주제가 블록 발행이라 날짜와 분리 불가(§17.5). 교차 배치 전에는 읽지 않는다.

### 영구 수동 (API에 없음) — 2주에 한 번이면 충분
```
주요 조회 출처 (릴스 탭 / 탐색 탭 / 피드)      또래 계정 대비 평가 (더 높음 / 더 낮음)
```

## 진행 상태 — 완료
- [x] 1~4. 레퍼런스 4개 전수 전사 + 실제 API 판정
- [x] 5. 코드 반영 (`ig_catalog.py` 출처, `insights.py` 전수 수집, 계정 차원 신설)
- [x] 6. 정기 수집 (`insights.yml` 매일 03:20 KST + `ig_probe.py --if-stale` 25일마다)
- [x] 7. 쓸 것 선정(위) + `RULES.md` G-3 + `test_catalog.py` + `check_rules.py`
