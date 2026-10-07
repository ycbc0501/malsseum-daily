# 인사이트를 자동화하는 법 — 그리고 두 달 동안 무엇이 틀렸는가

**2026-10-07.** 원석님 질문: *"그럼 api로 못받는거야? 매번수동으로 줘야해?"*

**답: 못 받는 게 아닙니다. 권한 하나가 빠져 있었고, 아무도 토큰에게 물어본 적이 없습니다.
매번 수동도 아닙니다 — 손으로 넣던 13칸 중 10칸이 자동이 됩니다.**

---

## 1. 실제로 무엇이 문제였나 (추측 아님, 호출 결과)

```
GET /debug_token  (2026-10-07 실행)
  type    SYSTEM_USER        application  bible        expires_at  0 (만료 없음)
  scopes  pages_show_list · instagram_basic · instagram_manage_comments
          instagram_content_publish · pages_read_engagement · public_profile
```

**`instagram_manage_insights`가 목록에 없습니다.** 요청된 적이 없습니다.

두 달 동안 로그에 찍힌 `(#10) Application does not have permission for this action` 을
**"인스타그램이 우리에게 안 보여준다"** 로 읽었습니다. 실제 뜻은 **"이 토큰은 그걸 요청한
적이 없다"** 입니다. 메시지는 처음부터 정확했습니다.

> **규칙으로 승격:** 권한은 추측하지 않는다. `python3 ig_doctor.py` 가 1초 만에 답한다.

### 1.1 그 과정에서 배운, 사람을 속이는 동작 하나

권한이 없을 때 Meta 는 **존재하지 않는 지표 이름에도 `(#10)`** 을 돌려줍니다. 실제로
`view_sources`, `navigation` 같은 가짜 이름까지 전부 `(#10)` 이었습니다. **권한 검사가 이름
검증보다 먼저** 일어납니다. 그래서 `(#10)` 쓸어보기로 "이 지표가 있나 없나"를 판정할 수
없습니다. **근거는 공식 레퍼런스뿐입니다.**

### 1.2 지난 세션에 제가 한 "확인"은 아무것도 확인하지 못했습니다

`ig_login.py --auth-url` 이 만드는 주소가 **HTTP 200** 을 돌려주는 걸 보고 "경로가 살아있다"고
보고드렸습니다. 대조 시험을 해보니 **존재하지 않는 앱 ID(`1234567890123456`)도 완전히 같은
200 로그인 페이지**를 돌려줍니다(본문 길이 680,448 대 680,370). **200은 증거가 아닙니다.**

---

## 2. 그래서 무엇이 자동이고 무엇이 영영 수동인가

### 2.1 권한만 붙으면 **자동** — 릴 미디어 인사이트 (공식 레퍼런스 2026-10-07 원문)

```
comments · crossposted_views · facebook_views · ig_reels_avg_watch_time
ig_reels_video_view_total_time · likes · reach · reels_skip_rate · reposts
saved · shares · total_interactions · views · total_comments · total_likes · total_views
```

**`reels_skip_rate` 와 `reposts` 가 API 에 있습니다.** 어제 손으로 넣은 「건너뛰기 85.2%」와
「리포스트 0」이 그것입니다. 레퍼런스상 `reels_skip_rate` 는 *"릴 첫 3초 안에 건너뛴 사람의
조회 비율"* 이고 *"추정치이며 개발 중"* 이라고 명시돼 있습니다.

> **이건 Meta 탓이 아니라 우리 탓입니다.** `post_instagram.INSIGHT_TIERS` 가 이 두 이름을
> **한 번도 요청한 적이 없습니다.** 권한이 생겼어도 안 들어왔을 것입니다. 오늘 고쳤습니다.

### 2.2 API 에 **없는** 것 — 계속 손으로 (그리고 이게 전부입니다)

| 화면 | 왜 수동인가 |
|---|---|
| 주요 조회 출처 (릴스 탭 / 탐색 탭 / 피드) | 미디어 단위 출처 분해가 API 에 없음 |
| 또래 계정 대비 (더 높음 / 더 낮음) | 앱 전용 비교, API 미노출 |
| 팔로우 (이 릴에서 생긴) | 미디어 단위 `follows` 는 릴에 유효하지 않음 |

**세 칸뿐이고, 셋 다 천천히 변합니다.** 매일이 아니라 **2주에 한 번 한 건**이면 충분합니다.

```
어제 손으로 넣은 13칸  →  자동 10칸 + 수동 3칸
```

---

## 3. 사람이 한 번만 하면 되는 일

**자동 갱신은 이미 만들어져 있습니다**(`.github/workflows/refresh-token.yml` +
`refresh_token.py`). 최초 승인 1회만 남았습니다. 그 뒤로는 손댈 일이 없습니다.

### 경로 B — 인스타그램 로그인 (권장, 페이스북 계정 불필요)

기존 발행 토큰은 **건드리지 않습니다.** 읽기 전용 토큰을 따로 만듭니다.

```
1. developers.facebook.com → 앱 "bible" → 제품에 "Instagram" 추가
   → "API setup with Instagram login" → Instagram 앱 ID / 시크릿을 복사

2. export IG_APP_ID=...  IG_APP_SECRET=...
   python3 ig_login.py --auth-url
   → 출력된 주소를 열고 @saintseoul_studio 로 로그인 → 승인
   → https://localhost/?code=XXXX 로 이동(페이지는 안 열립니다. 정상입니다)

3. python3 ig_login.py --code 'XXXX'        # 60일 토큰 출력
   gh secret set IG_INSIGHTS_TOKEN          # 붙여넣기

4. python3 ig_doctor.py                     # ✅ 가 뜨는지 확인
```

**과거 기록상 경로 A(비즈니스 관리자에서 시스템 사용자 토큰에 권한 추가)는 SMS 2FA 에
막혀 있었습니다.** 그게 풀렸다면 경로 A 가 더 낫습니다 — 만료 없는 토큰 하나로 끝나고
갱신이 아예 필요 없습니다. 2FA 를 인증 앱으로 바꿀 수 있으면 먼저 시도해 볼 값이 있습니다.

### 검증 — 승인 전에도, 승인 후에도 같은 한 줄

```
python3 ig_doctor.py
```

권한 유무 · 어떤 권한이 빠졌는지 · 무엇이 자동화되는지 · 무엇이 수동으로 남는지를
한 화면에 출력합니다. **추측하지 않고 토큰에게 묻습니다.**

---

## 4. 오늘 같이 고친 잠복 버그 — 이게 없었으면 승인해도 헛수고였습니다

`insights.py api()` 는 인스타그램 로그인 토큰이 **`graph.instagram.com`** 에만 유효하다는
걸 알고 있었는데, **`post_instagram.insights()` 에게 그걸 전달하지 않았습니다.** 항상
`graph.facebook.com` 으로 호출했습니다.

```
원석님이 OAuth 를 통과시킨다 → 토큰이 생긴다 → 호출이 OAuth 오류로 실패한다
→ insights() 가 {} 를 돌려준다 → 로그에 "insights unavailable" 이 찍힌다
→ 권한이 없을 때와 글자 하나 다르지 않다
```

**승인하고도 "역시 안 되네"로 끝났을 것입니다.** `insights(media_id, token, base=...)` 로
고쳤습니다.

---

## 5. 그래서 바뀐 것

- `post_instagram.py` — `INSIGHT_TIERS` 에 `reels_skip_rate · reposts ·
  ig_reels_video_view_total_time` 추가, `INSIGHT_SINGLES` 분리, `base` 인자 추가
- `insights.py` — `base` 를 실제로 넘김
- `ig_doctor.py` — **신규.** 권한을 묻는 한 줄짜리 진단
- `RULES.md` G-2 — "API 는 도달을 줄 수 없다"는 **거짓 서술을 정정**
- `test_insight_metrics.py` — 레퍼런스 목록과 코드가 어긋나면 실패
