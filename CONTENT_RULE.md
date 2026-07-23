# THE CONTENT RULE — @to_light_bible constitution

The single source of truth for what this account posts and how. **Every change to the pipeline must be
checked against ALL of these rules before it ships.** If a change would break a rule, the change is
wrong — not the rule. Where a rule names code, the code is the enforcement; the rule is the intent.

Voice: a Korean daily Bible-verse account (말씀) whose whole feeling is **밝고 희망참 (bright & hopeful)**
— uplifting, warm, peaceful and full of light — while staying **real, reverent and hyperrealistic**
(경건함 유지). Never dark/gloomy, and never cute, kitschy, twee, saccharine, or fake/CGI. (Direction
changed 2026-07-23 from the earlier dark/heavy/moody look → generally bright and hopeful; a few
naturally-darker-but-hopeful scenes — stars, candle, dusk — remain as a small minority for range.)
Fully hands-off: it runs itself; a human should never need to approve a post.

---

## 1. Cadence — twice a day, forever
- **Two posts daily: 05:00 and 19:00 KST** (±10 min jitter). GitHub Actions cron (`.github/workflows/daily-post.yml`), which fires early and then `daily_post.py` waits for the exact target time.
- Never more, never fewer. Both posts follow every rule below.

## 2. Themes — at least 20, always rotating, never overlapping
- `fetch_higgsfield.SCENE_GROUPS` holds **≥20 distinct visual themes** (currently 25), each bright & hopeful (경건함 유지): sea, forest path, cathedral, misty mountain, rainy street, wheat field, reflection lake, lighthouse, snowfall, canal town, chapel, wilderness, window, river, archway/ruins, blossom, starfield, harbor, winter trees, candle, storm sky, rain pond, shore, waterfall, dusk sky (어스름).
- Themes are **round-robin interleaved** into the flat `SCENES` list so sequential rotation walks through *different* themes; the dict order alternates families (water / dry land / architecture / interior) so neighbours never look alike.
- `pick_scene()` + the `used_scene_cats` ledger in `state.json` **skip forward past any theme used in the last 2 posts** — a gate rejection or fallback can never cluster the same theme. Invariant: **no two consecutive posts share a theme.**

## 3. Even the same theme must look substantially different
When a theme comes round again it must differ by multiple axes:
- **Base variant:** each theme has ≥2 differently-worded scene prompts.
- **Light / colour palette:** `LIGHT` (5 options, all bright & hopeful) — bright clear morning, soft luminous daylight, warm golden sunlight, fresh sparkling after-rain, gentle glowing dawn. Keyed on the **monotonic `post_i` counter**; 5 does not divide the ~24-post theme cycle, so a theme cycles through all five palettes across its appearances.
- **Camera vantage / angle:** `VANTAGE` (4 options) — wide/distant, low eye-level, high looking-out, intimate close.
- These are set in `scene_variation(post_i)` and injected into every prompt. Axes to keep leveraging: colour, angle, narrative, time-of-day feel, season, age/era.

## 3b. Every post is VIDEO, and every image is HYPERREALISTIC
- **Production posts are always Reels (.mp4)** — never a static image post. `daily_post.py` always builds and publishes a video via `publish_reel`. (Preview-page stills are illustrations only, not production.)
- The still-Ken-Burns fallback is *still an .mp4*, used only when Veo motion fails the gate/errors — a rare safety net, not a static post.
- **Every rendered image must be HYPERREALISTIC — indistinguishable from a genuine photograph.** `QUALITY` enforces this in prose (one clean realism statement, NOT stacked hype-words like "8k ultra" which backfire on this model → baked text / game look). Absolutely no glossy CGI, 3D render, video-game frame, digital painting, or plasticky AI look.

## 4. Physics must be real — nothing impossible
- ONE horizon; sky above, ground/water below. **No** stacked/doubled scenes, **no** two water surfaces, **no** vertical mirror (upside-down land hanging from the top), **no** framed-inset/collage/photo-in-photo.
- Any reflection is a **physically-correct upside-down mirror** (roofs point down) — never a second upright "town in the water."
- Water falls **down** (waterfalls), etc. Enforced by the `EVENTONE` prompt rule **and** the VLM composition gate.
- **Composition gate:** `check_composition()` (gemini-2.5-pro, `_CHECK_PROMPT`) inspects every render for vertical-mirror / stacked-duplicate / wrong-reflection / fake-CGI / warped structures; `generate_checked()` regenerates up to 3×. Best-effort (never blocks a post on a flaky check), but it is the substitute for a human eye — keep it strict without false-flagging normal single-horizon landscapes.

## 5. Motion — real-time, calm, never fast
- Veo prompt (`fetch_veo.py`) forces **real-time 1× playback, ~8s, camera locked, clouds barely moving**. No artificial slow-mo / interpolation / frozen-sky compositing (they bug out and look weird).
- **Motion gate:** `make_video.motion_score()` with `MOTION_MAX=2.6`, `SKY_MAX=0.7`. Too-fast clip → retry once → still too fast → fall back to a **calm still**. A frantic clip can never post itself.

## 6. Video length — and NEVER reverse playback
- **NEVER boomerang / reverse / ping-pong the clip.** Playing footage backwards is banned artificial post-processing (water and light running backwards read as fake), same rule as no slow-mo and no interpolation. Video always plays **forward at native speed**.
- Length must come from **Veo itself**, never from replaying frames. Veo's fast tier caps at ~8s; to go longer, chain a genuine continuation (feed the clip's last frame back into Veo) — never a reverse or a hard loop.
- Still fallbacks run **24s**.

## 7. Music — unique every time, warm but small
- A **unique Lyria hymn per post** (`fetch_lyria.py`): warm, hopeful, major-key church-hymn spirit — **not sad, not big**; kept **small, quiet, sparse, intimate**; never loud/grand/swelling. Mixed in **soft (volume 0.4)**.
- Fallback: the vetted royalty-free library via `pick_music()`, which has a **no-repeat ledger** (`used_music`) and **family-interleave** so the same *sound* never lands on consecutive posts. **Never repeat music.** No auto-downloaded internet music (Content-ID risk).

## 8. Verses never repeat (books may)
- **Never repeat a verse:** `used_verses` ledger; the whole pool cycles before any verse repeats. This is the hard rule.
- **Books MAY overlap** — no book-level restriction. There is only a *soft* least-posted-book-first tiebreak for gentle balance; it never forbids a book.
- Weekly **theme series** (`THEME_ORDER`) gives the feed meaning.
- Never post a verse that ends mid-clause (`INCOMPLETE_ENDINGS`).

## 9. Text & format — consistent, centered, readable
- Verse text is **always centered**, in the **NanumMyeongjo serif** at a fixed size, wrapped so it never splits a verb phrase / modifier-head pair (`generate.py`).
- Every scene prompt keeps the **center of the frame soft and open** (`COMPOSE`) so the verse is always legible over it.
- **Same letter format on every post** — do not change the font, size logic, or centering without a deliberate decision recorded here.

## 10. Caption & comment
- **Caption:** verse text + `[book chapter:verse]` reference + a gentle follow CTA.
- **First comment:** the hashtag set (`HASHTAGS`). Reference/book handling stays **as it is now** (shown on-image + in caption; hashtags in the comment).

## 11. No-repeat ledgers (all in `state.json`, committed back after each run)
`used_verses`, `used_music`, `used_scene_cats`, `scene_i`, `post_i`, `music_i`, `used_photos`, `used_clips`.
Every rotating resource has a ledger and cycles the whole set before repeating. Perceived sameness counts as a repeat, not just literal file reuse.

## 12. Fallback chain (stay alive, always on-brand)
- Image gen down → licensed photo pool (`used_photos` ledger).
- Veo down / too fast → calm still zoom (24s).
- Lyria down → vetted music library (no-repeat).
None of the fallbacks may violate rules 2–10.

---

### Governance
On **every** update to the pipeline, re-read this file and confirm each rule still holds. Update this
file in the same change whenever a rule intentionally changes, so it never drifts from the code.
