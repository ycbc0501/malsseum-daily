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

**사람만 할 수 있는 0순위 (이제 하나만 남음):** `IG_INSIGHTS_TOKEN` 발급(`ig_login.py`).
지금 인사이트 전 항목이 `(#10)`으로 거부돼 도달·공유·저장을 하나도 못 본다.
제한이 풀린 지금이야말로 그 숫자가 의미를 갖는다.

비용: 실측 Veo 40.3초/건 → 월 ≈₩334,000(총 ≈₩390,000, 한도 ₩260,000). 수정안은 STRATEGY.md §6.

Pipeline entry point: `daily_post.py` (orchestrator) → `fetch_higgsfield.py` (image + gates),
`fetch_veo.py` (motion), `fetch_lyria.py` (music), `make_video.py` (reel), `generate.py` (text),
`post_instagram.py` (publish — and it is the CLI, not `daily_post.py`, that actually
publishes in CI). No-repeat ledgers live in `state.json`; performance in `metrics.json`
(`metrics.py`, backfilled by `insights.py`); comment replies in `comments.json`.
