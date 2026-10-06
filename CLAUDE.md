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

## 현재 상태 — 2026-10-06, 전략 재검토 완료 (읽고 시작할 것)

**[notes/strategy/STRATEGY.md](notes/strategy/STRATEGY.md)** 가 지금 이 계정의 제1 문서다.
파이프라인을 더 다듬기 전에 그걸 읽어야 한다 — **막힌 곳이 품질이 아니기 때문이다.**

측정된 사실 세 줄:
- 릴 도달 ≈ 팔로워 수(비팔로워 유입 ≈0)인데 **본 사람의 7~14%가 좋아요를 누른다.**
  보여주면 좋아한다. 안 보여주고 있을 뿐이다.
- 인스타그램이 **"팔로워가 아닌 사람에게 추천될 수 없습니다"** 상태로 걸어놨고
  범주는 **「복제된 콘텐츠 또는 권리 미소유 콘텐츠」** 다. 확인된 10건 중 7건이 플래그.
- 자격은 **마지막 비원본 게시물로부터 30일** 뒤 롤링으로 복구된다
  → **템플릿 그대로 하루 2번 올리는 것이 그 시계를 매일 리셋한다.**

**사람만 할 수 있는 0순위 (아직 안 됨):** ①계정 상태 화면 확인 ②**「검토 요청」 누르기**
③`IG_INSIGHTS_TOKEN` 발급(`ig_login.py`, 지금 인사이트 전 항목 `(#10)` 거부)
④Trial Reels 토글 확인.

비용: 실측 Veo 40.3초/건 → 월 ≈₩334,000(총 ≈₩390,000, 한도 ₩260,000).
**과금 초의 62.7%가 반려된 연결 세그먼트로 버려진다.** 수정안은 STRATEGY.md §6.

Pipeline entry point: `daily_post.py` (orchestrator) → `fetch_higgsfield.py` (image + gates),
`fetch_veo.py` (motion), `fetch_lyria.py` (music), `make_video.py` (reel), `generate.py` (text),
`post_instagram.py` (publish — and it is the CLI, not `daily_post.py`, that actually
publishes in CI). No-repeat ledgers live in `state.json`; performance in `metrics.json`
(`metrics.py`, backfilled by `insights.py`); comment replies in `comments.json`.
