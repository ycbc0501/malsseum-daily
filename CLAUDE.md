# Saint Seoul (@saintseoul_studio) — daily 말씀 auto-poster

This repo runs a fully hands-off Korean daily Bible-verse Instagram account for the
**Saint Seoul** brand (@saintseoul_studio, renamed 2026-08-13 from @to_light_bible).
The numeric `IG_USER_ID` is unchanged by the rename, so nothing in the API path breaks;
the handle is never hardcoded (`post_instagram.username()`).

**Before making ANY change to the posting pipeline, read [CONTENT_RULE.md](CONTENT_RULE.md) — the
content constitution — and verify every rule still holds after your change.** If a rule intentionally
changes, update CONTENT_RULE.md in the same commit so it never drifts from the code.

Pipeline entry point: `daily_post.py` (orchestrator) → `fetch_higgsfield.py` (image + gates),
`fetch_veo.py` (motion), `fetch_lyria.py` (music), `make_video.py` (reel), `generate.py` (text),
`post_instagram.py` (publish). No-repeat ledgers live in `state.json`.
