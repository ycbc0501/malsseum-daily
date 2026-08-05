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
- **Timing budget:** the cron fires ~2h early (GitHub's scheduler runs 1–2h late), so the job spends
  **up to 130 min sleeping** before it starts working. `timeout-minutes` must therefore cover
  **wait + build (~50 min) — i.e. stay ≥ 180.** Sizing it to the build alone silently kills posts
  mid-render on days the scheduler fires late (this ate the 07-24 and 07-26 morning posts).
- **A missed post is never silent:** any failed/cancelled run opens a GitHub issue.

## 2. Themes — at least 20, always rotating, never overlapping
- `fetch_higgsfield.SCENE_GROUPS` holds **≥20 distinct visual themes** (currently 25), each bright & hopeful (경건함 유지): sea, forest path, cathedral, misty mountain, rainy street, wheat field, reflection lake, lighthouse, snowfall, canal town, chapel, wilderness, window, river, archway/ruins, blossom, starfield, harbor, winter trees, candle, storm sky, rain pond, shore, waterfall, dusk sky (어스름).
- Themes are **round-robin interleaved** into the flat `SCENES` list so sequential rotation walks through *different* themes; the dict order alternates families (water / dry land / architecture / interior) so neighbours never look alike.
- `pick_scene()` + the `used_scene_cats` ledger in `state.json` **skip forward past any theme used in the last 2 posts** — a gate rejection or fallback can never cluster the same theme. Invariant: **no two consecutive posts share a theme.**

## 3. Even the same theme must look substantially different
When a theme comes round again it must differ by multiple axes:
- **Base variant:** each theme has ≥2 differently-worded scene prompts.
- **Light / colour palette:** `LIGHT` (5 options, all bright & hopeful) — bright clear morning, soft luminous daylight, warm golden sunlight, fresh sparkling after-rain, gentle glowing dawn. Keyed on the **monotonic `post_i` counter**; 5 does not divide the ~24-post theme cycle, so a theme cycles through all five palettes across its appearances.
- **Camera vantage / angle:** `VANTAGE` (4 options) — wide/distant, low eye-level, high looking-out, intimate close.
- **Scale / grandeur (웅장함):** `SCALE` (3 options) — monumental forms at the edges, vast atmospheric depth, a small element dwarfed to reveal scale. Skipped for the *intimate close* vantage, where "come close" and "be monumental" would contradict each other.
- These are set in `scene_variation(post_i)` and injected into every prompt. Axes to keep leveraging: colour, angle, narrative, time-of-day feel, season, age/era.
- Periods are deliberately **coprime** (LIGHT 5 / SCALE 3, VANTAGE every 5th post) so a theme meets a fresh light+scale pairing for 15 posts before any combination recurs.

**Grandeur must never be bought with legibility.** The verse is the point of the account, so `COMPOSE`'s
soft-open centre wins every time. Scale is therefore built *outside* the centre — depth, atmospheric
perspective, immensity at the frame edges, scale contrast — never by parking a huge subject in the
middle. Reference for the intended feeling: **@fuezstudio** (웅장 + 사실적), alongside @wondervisionary.

## 3b. Every post is VIDEO, and every image is HYPERREALISTIC
- **Production posts are always Reels (.mp4)** — never a static image post. `daily_post.py` always builds and publishes a video via `publish_reel`. (Preview-page stills are illustrations only, not production.)
- **Every post also goes to Stories** (`post_instagram.publish_story`, `media_type=STORIES`). `share_to_feed` on a Reel only places it in the profile GRID — a story is a separate publish, and without it the account has no story presence at all. Best-effort: a failed story never fails a post that already published.
- The still-Ken-Burns fallback is *still an .mp4*, used only when Veo motion fails the gate/errors — a rare safety net, not a static post.
- **Every rendered image must be HYPERREALISTIC — indistinguishable from a genuine photograph.** `QUALITY` enforces this in prose (one clean realism statement, NOT stacked hype-words like "8k ultra" which backfire on this model → baked text / game look). Absolutely no glossy CGI, 3D render, video-game frame, digital painting, or plasticky AI look.
- **Realism is asked for in camera terms, not declared.** `QUALITY` names what a real lens actually does — natural depth of field with the far distance falling off, uneven organic detail (never a uniformly repeating grass carpet), restrained true-to-life colour, no HDR boost, no airbrushed smoothness, no edge glow. Declaring "hyperrealistic" is not enough on its own.
- **Plain scenes are judged hardest.** An open field, a bare hillside or a plain sky has no complexity to hide the AI tells behind, so `_CHECK_PROMPT` clause 4 is explicitly *strictest* on simple scenes — a plain scene that looks even somewhat rendered is rejected. (Added 2026-08-05 after a simple field published looking obviously fake.)

## 4. Physics must be real — nothing impossible
- ONE horizon; sky above, ground/water below. **No** stacked/doubled scenes, **no** two water surfaces, **no** vertical mirror (upside-down land hanging from the top), **no** framed-inset/collage/photo-in-photo.
- Any reflection is a **physically-correct upside-down mirror** (roofs point down) — never a second upright "town in the water."
- Water falls **down** (waterfalls), etc. Enforced by the `EVENTONE` prompt rule **and** the VLM composition gate.
- **Composition gate:** `check_composition()` (gemini-2.5-pro, `_CHECK_PROMPT`) inspects every render for vertical-mirror / stacked-duplicate / wrong-reflection / fake-CGI / warped structures; `generate_checked()` regenerates up to 3×. Best-effort (never blocks a post on a flaky check), but it is the substitute for a human eye — keep it strict without false-flagging normal single-horizon landscapes.

## 5. Motion — real-time, calm, never fast
- Veo prompt (`fetch_veo.py`) forces **real-time 1× playback, ~8s, camera locked, clouds barely moving**. No artificial slow-mo / interpolation / frozen-sky compositing (they bug out and look weird).
- **Motion gate:** `make_video.motion_score()` with **`MOTION_MAX=2.0`, `SKY_MAX=0.45`**. Up to **three** Veo attempts, **keeping the calmest** (ranked on the worse of the two normalised axes) rather than the first one that squeaks under the bar; still too fast → fall back to a **calm still**. A frantic clip can never post itself.
- **Tightened 2026-08-05.** The old 2.6/0.7 sat roughly twice the measured calm reference (1.7/0.35) and let visibly racing clouds and churning water reach the feed. Keeping the calmest of three attempts is what makes the tighter bar affordable — without it, a stricter threshold only buys more still fallbacks instead of better motion.
- The rule-6 continuation chain seeds from that **calmest** take, not from whichever attempt Veo generated last — otherwise a rejected frantic opening would still set the motion for every segment after it.

## 6. Video length — and NEVER reverse playback
- **NEVER boomerang / reverse / ping-pong the clip.** Playing footage backwards is banned artificial post-processing (water and light running backwards read as fake), same rule as no slow-mo and no interpolation. Video always plays **forward at native speed**.
- Length must come from **Veo itself**, never from replaying frames. Veo's fast tier caps at ~8s; to go longer, chain a genuine continuation (feed the clip's last frame back into Veo) — never a reverse or a hard loop.
- **Production reels are ~16s: `daily_post.SEGMENTS = 2` chained continuations.** Each segment
  animates the *tail* frame of the one before it (`make_video.last_frame`, taken `TAIL` before the
  end so Veo's frozen last frames never seed or show), and the segments are joined forward-only
  (`make_video.chain_clips`). No frame is ever repeated or reversed.
- **The motion gate applies to every segment**, not just the first. A continuation gets one
  attempt and no retry: if it errors or comes back too fast we publish the segments that passed,
  so a bad continuation costs *length*, never the post.
- **Raising `SEGMENTS` is a timing-budget decision, not a free knob** — each segment is another
  Veo call (~2–6 min) against rule 1's ~50 min of build time, and past ~30s the reel outlasts
  Lyria's 30s hymn, which would force the music to loop (rule 7 keeps it seamless).
- Still fallbacks run **24s** — already longer than the chained reel, so they are not doubled.

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
- The **photo pool obeys the same soft-centre rule**: `generate.calm_photos()` filters out photos whose
  centre band is too chaotic to carry text (stained glass, dense foliage) before any pick — carousel
  and daily fallback both. And when a busy background does get through, `render()`'s backing strength
  is keyed to the **brightest patches under the text (90th percentile), not the band average** — a
  dark-averaging photo with bright patches (the 2026-07-26 stained-glass carousel) must still read —
  plus a wide feathered scrim under the backing when the band is very busy. **Legibility beats the
  photo; the verse is the point.**
- **Same letter format on every post** — do not change the font, size logic, or centering without a deliberate decision recorded here.

## 10. Caption & comment
- **Caption:** verse text + `[book chapter:verse]` reference + a **share ask first, follow ask second**.
- **The share ask outranks the follow ask, deliberately.** Instagram's stated ranking signals are watch time, **sends per reach** and likes per reach, and a send weighs several times a like in deciding whether to show a post to non-followers. A follow can only come from the already-convinced, so leading with it spends the strongest line of the caption on the weakest signal. Asking someone to forward a 말씀 to a person who needs it is simultaneously the higher-weighted action and the account's honest purpose. Measured per post as send/reach by `insights.py` — if the data says otherwise, change it back and record that here. (Changed 2026-08-05.)
- **First comment:** the hashtag set (`hashtags.build`). Reference/book handling stays **as it is now** (shown on-image + in caption; hashtags in the comment).
- **Exactly 5 hashtags — never more.** Instagram capped posts and reels at 5 in December 2025,
  and the cap counts caption + comments **together**, so putting them in the first comment buys
  no extra slots; over the cap Instagram strips the excess or refuses the publish. `hashtags.MAX`
  is that cap and `build()` enforces it. (The old fixed 7-tag string was over the limit.)
- Tags are **chosen for the verse's theme**, not to fish for reach — Instagram's own position is
  that hashtags label a topic rather than distribute content, so 5 accurate tags beat 5 broad
  ones. `hashtags.SETS` is a plain lookup table, one fixed set per theme.
- **Deliberately NOT rotated.** The no-repeat ledgers in rule 11 exist because a reader
  *experiences* a repeated image or hymn as staleness; nobody experiences hashtag sameness.
  Rotation here would be moving parts serving nothing, so the table stays a table.

## 10b. Direct messages — ONE gift, never a pitch
- The account **never cold-DMs anyone.** Meta's Instagram API has no outbound endpoint for it,
  and mass unsolicited DMs would cost us the account. The only DM we ever send is a **Private
  Reply**: Meta allows **exactly one message per comment**, within **7 days** of it.
- That message **asks for nothing** — no follow request, no link. Meta's spam policy names
  follows explicitly as something you may not charge for content, and a DM to a non-follower
  lands in their Requests folder anyway. It carries the **기도문 for the theme of the verse they
  commented on** (`dm_reply.compose`), and nothing else.
- **Never a second message.** No sequence, no follow-up, and deliberately **no reply bait** —
  a reply would open Meta's 24-hour window, but this account is hands-off, and inviting someone
  to share a burden nobody will read is worse than staying quiet. One gift, then silence.
- `replied_comments` makes one-per-comment a **hard invariant** (a poller re-sees every comment;
  Meta allows one). Wording rotates via `dm_i` so the account never emits identical text
  repeatedly — same principle as rule 11.
- **Not wired up:** no workflow calls `dm_reply`, and `reply_to_new_comments()` defaults to
  dry-run, until `instagram_manage_messages` clears App Review.

## 10c. Comment replies — 🙏, in public, about half an hour later
- **Every comment gets a reply**, in-thread and public: `🙏` or `아멘🙏`, nothing more
  (`comment_reply.py`). In-thread replies use `instagram_manage_comments` — the permission the
  hashtag first-comment already holds — so unlike the private reply in 10b this works today.
- **Never instant.** Each comment draws its own target time of **comment + 10–50 min** (≈30 ± 20)
  once, when first seen, and the target is remembered so a stateless cron still honours it. An
  instant reply is the single thing that makes a warm gesture read as a machine.
- **Exactly one reply per comment**, enforced by the `replied_publicly` ledger — the poller
  re-sees every comment on every run. Our own hashtag comment is skipped by username. (Named
  apart from 10b's `replied_comments` on purpose: one records a public reply, the other a DM,
  and a shared name across two files would eventually get them confused.)
- **No backlog burst.** A comment already older than 24h when first seen is marked handled
  *without* replying: a first deploy answering months of comments at once is precisely the bot
  behaviour the delay exists to prevent.
- Polled every 10 minutes by `.github/workflows/comment-reply.yml`. GitHub's scheduler drifts
  (see rule 1), so the ~30 min target is best-effort, never a guarantee.

## 11. No-repeat ledgers (all in `state.json`, committed back after each run)
`used_verses`, `used_music`, `used_scene_cats`, `scene_i`, `post_i`, `music_i`, `used_photos`,
`used_clips`, `posted_media` (media id → theme, for 10b), `replied_comments` (10b, DMs), `dm_i`.
Every rotating resource has a ledger and cycles the whole set before repeating. Perceived sameness counts as a repeat, not just literal file reuse.

**Two ledgers live in their own files, on purpose:** `comments.json` (`replied_publicly`,
`pending_replies`, `reply_i` — rule 10c) and `insights.json` (rule 13). Both are written by
crons that run far more often than the poster, and two jobs rebasing the same one-line
`state.json` is a merge conflict waiting to happen. Separate files never collide.

## 12. Fallback chain (stay alive, always on-brand)
- Image gen down → licensed photo pool (`used_photos` ledger).
- Veo down / too fast → calm still zoom (24s).
- Lyria down → vetted music library (no-repeat).
None of the fallbacks may violate rules 2–10.

## 13. Measure, don't guess
- The account ran its first ~70 posts without reading back a single number, so every content
  decision was an assumption. `insights.py` collects per-post metrics (views, reach, likes,
  comments, saved, shares) plus the daily follower count into `insights.json` nightly
  (`.github/workflows/insights.yml`), joined to each post's verse and theme.
- **Old posts join by verse reference.** The caption carries `[book chapter:verse]`, so posts
  published long before any bookkeeping existed still resolve to a theme via `verses.json`.
- **Metric availability is probed, never assumed.** Meta rejects an entire insights request if
  any single metric is unsupported for that media type, and the supported set changes between
  API versions. `insights.py` tries the full set, falls back to probing one at a time, and
  caches the working set per media type in `metrics_ok`. A metric Meta stops serving degrades
  the report; it must never crash the job.
- **The headline number is send/reach**, not likes — see rule 10. Anything that claims to
  improve the account should be checkable against this ledger, and a claim that cannot be
  checked against it is an opinion.

---

### Governance
On **every** update to the pipeline, re-read this file and confirm each rule still holds. Update this
file in the same change whenever a rule intentionally changes, so it never drifts from the code.
