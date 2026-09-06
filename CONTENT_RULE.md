# THE CONTENT RULE — Saint Seoul (@saintseoul_studio) constitution

The single source of truth for what this account posts and how. **Every change to the pipeline must be
checked against ALL of these rules before it ships.** If a change would break a rule, the change is
wrong — not the rule. Where a rule names code, the code is the enforcement; the rule is the intent.

Voice: a Korean daily Bible-verse account (말씀) whose whole feeling is **고요함 (quiet & still)** —
calm, peaceful, tender and reverent — while staying **real and hyperrealistic** (경건함 유지). Never
cute, kitschy, twee, saccharine, or fake/CGI.

**The criterion is QUIET, not brightness** (direction changed 2026-07-30, superseding the bright-only
direction of 2026-07-23). A pale dawn sky and a lamp-lit room after dark are **both** on brand; the
full tonal range is open — night sea, starfield, dusk, a dim interior, blue hour. What is banned is
**gloom**: ominous, oppressive, bleak, sorrowful, frightening or heavy. A quiet dark is peaceful; a
gloomy dark is not.

**The 말씀 LEADS; the image accompanies it.** This is the account's ordering rule and it outranks any
visual ambition. The frame is deliberately under-stated — plain, simple, lots of empty space — because
a spectacular photograph competes with the verse and wins. Reference: **@dailymayim** (말씀 우선, 일상적
이고 고요한 사진). Fully hands-off: it runs itself; a human should never need to approve a post.

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
- `fetch_higgsfield.SCENE_GROUPS` holds **≥20 distinct visual themes** (currently 36) in two families:
  - **Quiet nature & architecture:** sea, forest path, cathedral, misty mountain, rainy street, wheat field, reflection lake, lighthouse, snowfall, canal town, chapel, wilderness, river, archway/ruins, blossom, starfield, harbor, winter trees, storm sky, rain pond, shore, waterfall, dusk sky (어스름), candle, still water.
  - **Everyday & intimate** (added 2026-07-30, the @dailymayim register): window light, bedroom, lamp-lit room, flowers in a vase, curtain, desk, café table, alley, city at night, field flowers, country road. This family exists **because it lets the verse lead** — an ordinary room has far less to say than a monumental landscape.
- **Base prompts name the SUBJECT and weather ONLY — never the time of day, never the brightness.**
  Tone comes from the rotating `LIGHT` palette. This was always the documented design but was
  violated in practice: the prompts carried **109 hardcoded tone words** ("bright" 46×, "sunlit" 22×,
  "sunlight" 20×), which is the real reason the account could only ever look bright — a dark palette
  would have contradicted the scene text itself. Keep tone words OUT of scene prompts.
- Themes are **round-robin interleaved** into the flat `SCENES` list so sequential rotation walks through *different* themes; the dict order alternates families (water / dry land / architecture / interior) so neighbours never look alike.
- `pick_scene()` + the `used_scene_cats` ledger in `state.json` **skip forward past any theme used in the last 2 posts** — a gate rejection or fallback can never cluster the same theme. Invariant: **no two consecutive posts share a theme.**

## 3. Even the same theme must look substantially different
When a theme comes round again it must differ by multiple axes:
- **Base variant:** each theme has ≥2 differently-worded scene prompts.
- **Light / colour palette:** `LIGHT` (**7 options spanning bright → dark**) — clear early morning, soft even daylight, warm low afternoon, pale quiet dawn, last quiet light of dusk, cool blue stillness after sunset, faint light after dark. Keyed on the **monotonic `post_i` counter**; 7 is prime and divides neither 36 (themes) nor 72 (scenes), so a theme never locks onto one tone.
- **Camera vantage / angle:** `VANTAGE` (4 options) — wide/distant, low eye-level, high looking-out, intimate close.
- These are set in `scene_variation(post_i)` and injected into every prompt. Periods stay **coprime**: LIGHT every post (7), VANTAGE every 7th post (4), so a theme meets a fresh light+angle pairing for 28 posts before any combination recurs.

### The 웅장함 (grandeur) axis is RETIRED — 2026-07-30
`SCALE` is gone. It was the instrument of an image-first post, and this account is verse-first: a
monumental frame competes with the 말씀 for attention and wins. The @dailymayim reference carries
almost no monumental imagery — windows, lamps, made beds, stems in a glass — and that is precisely why
the verse reads as the subject there. **Grandeur is no longer a variation axis**; the everyday/intimate
scene family in rule 2 replaces it. (@fuezstudio is no longer a reference for this account.)

**Understatement is a requirement, not a preference.** `QUALITY` asks for muted, slightly desaturated,
low-contrast, filmic colour with plenty of plain empty space — never vivid, glossy, dramatic or
spectacular. If a render is impressive, it is wrong.

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
- **An interior has no sky and no horizon — and the composition instruction must say so.**
  `COMPOSE` asks for an empty single-tone upper half and for detail anchored low. Filled with the
  landscape wording ("a clear cloudless sky", "a low horizon") for a *bedroom*, that is a
  contradiction, and the image model resolves it by **grafting an outdoor sky above the room** —
  a physically impossible composite. `generate_background()` therefore picks the empty-area and
  anchor wording by scene family (`INTERIOR_CATS`, `EMPTY_AREA`, `ANCHOR`): indoors the empty area
  is the room's own wall or ceiling, and there is no horizon. **The instruction caused the defect,
  not the model.** (Added 2026-08-21 after 에베소서 2:8 published as a room with sky above it.
  `cafe_table` is deliberately outdoors — a terrace needs its sky.)
- **When a scene family is added, the gate must be extended in the same change.** The five original
  gate clauses were all written for landscapes ("two horizons", "two bodies of water"), so when the
  07-30 direction added interior families nothing described a room-with-sky and it passed. Clause 6
  now covers indoor/outdoor composites — a window or open door showing a view is correct; outdoors
  where the wall or ceiling should be is not.
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

## 9. Text & format — verse-first, upper third, adaptive
- Verse text is **always centered horizontally**, in the **NanumMyeongjo serif** at a fixed size, wrapped so it never splits a verb phrase / modifier-head pair (`generate.py`).
- **The verse sits in the UPPER THIRD** (`placement = ("center", "top")`, block centred at 30% down), in
  a **narrow column** (0.68 of width, was 0.85) so lines come out short and stack into a compact centred
  text object. **That shape — not a bigger font — is what makes the 말씀 the subject.** The reference's
  type is no larger than ours; its verses lead because of position, emptiness and short lines.
- **`COMPOSE` keeps the UPPER HALF genuinely empty** and anchors the subject and all texture in the
  **lower third**, with nothing reaching up into the text area. (Was "soft-open centre" — which put the
  verse over the busiest part of the frame and is why heavy backing was ever needed.)
- **On-image citation** is set bare and small — `시편 100:5`, no brackets, 0.52× the verse size. The
  caption keeps the `[book chapter:verse]` form (rule 10).
- **Text colour is sampled from the background** (`band_color`): dark text on a light sky, light text on
  a dark one. Non-negotiable now that `LIGHT` runs from pale dawn to night — white-always was only safe
  while every scene was forced bright, and white on a pale dawn sky is invisible. Sampling a single
  still is sound because rule 5 pins the camera and keeps motion barely-there.
- **Backing is insurance, not the mechanism.** With an empty upper half and adaptive colour, the halo is
  dialled down to alpha 95 (was 150 — the visible grey smudge). It exists only to save a post when a
  render ignores `COMPOSE`; a compliant render should look like the reference, text straight on the photo.
- **The typeface never changes.** NanumMyeongjo, fixed size. Legibility is solved on the IMAGE side
  (below), never by altering the lettering.

### 9b. The text area is MEASURED, not hoped for
The verse must sit on **one precisely-contrasting tone**. `COMPOSE` asks the model for a single flat even
area — decisively light or decisively dark, never a middling mid-grey — but a prompt is a request, not a
guarantee, so the render is **measured and regenerated** like every other generator output.

- `generate.verse_ink()` renders the **real glyph mask** (geometry only, background-independent), and
  `text_area_contrast()` measures the candidate background *under exactly those pixels* — not an
  approximate band.
- **Worst-case, never the mean.** Which end is "worst" depends on the text colour: against light text the
  brightest pixels are the danger, against dark text the darkest. Measuring the mean is precisely what
  hid the 2026-07-26 stained-glass failure (dark average, bright panes under white strokes).
- Thresholds (`MIN_CONTRAST` 4.5 WCAG AA, `MAX_SPREAD` 22 gray stddev) are **empirical**, calibrated over
  the 100-photo pool: its best backgrounds score 3–9 spread / 12–19 contrast, its worst 65–75 / ~1.0.
  Contrast and flatness track each other almost perfectly — they are one property.
- A flat **mid-grey scores only 3.7 against either text colour** and is correctly rejected. That is why
  `COMPOSE` demands the tone be decisively light or decisively dark.
- `daily_post` retries up to **3** renders, advancing `post_i` each time so the light/angle changes
  rather than re-rolling the same prompt. The **photo-pool fallback is ranked by the same measurement**,
  so both paths obey one rule.
- **It never blocks a post.** If all attempts fail it ships with a `WARNING`, the backing carries it, and
  the measured `text_contrast` / `text_spread` go into `_meta.json` → `metrics.json` (rule 11b) so a bad
  text area is recorded rather than hidden — and can be correlated with performance.
- The **photo pool obeys the same soft-centre rule**: `generate.calm_photos()` filters out photos whose
  centre band is too chaotic to carry text (stained glass, dense foliage) before any pick — carousel
  and daily fallback both. And when a busy background does get through, `render()`'s backing strength
  is keyed to the **brightest patches under the text (90th percentile), not the band average** — a
  dark-averaging photo with bright patches (the 2026-07-26 stained-glass carousel) must still read —
  plus a wide feathered scrim under the backing when the band is very busy. **Legibility beats the
  photo; the verse is the point.**
- **Same letter format on every post** — do not change the font, size logic, or centering without a deliberate decision recorded here.

## 10. Caption & comment
- **Caption is the 말씀 and its reference. Nothing else.** No CTA, no brand line, no sell.
- **Everything that talks ABOUT the account lives in the first comment** (`hashtags.first_comment`):
  one quiet line (`FOLLOW_CTA`) then the five tags. Decided **2026-08-01** on evidence, and it is
  closer to retiring the CTA than relocating it — which is the honest description:
  - It was **already invisible**. Instagram folds the caption behind "더 보기", and on a real post
    the cut landed right after the reference, so the CTA shipped folded away.
  - It **contradicted the account**. This constitution says the verse leads, and rule 10b says the
    DM asks for nothing; the caption was the one place that still sold.
- **A share ask was briefly put back in the caption on 2026-08-05** by a branch that had not seen
  the 08-01 finding, on the reasoning that sends outrank likes as a ranking signal. That reasoning
  about *sends* is sound; putting it in the caption is not, because the caption is where it cannot
  be seen. Removed again 2026-08-13. If a share ask is ever wanted, the first comment is where it
  can actually be read.
- **This is measured, not assumed.** `daily_post.py` records `cta_in_caption` into `_meta.json`
  and `metrics.report()` groups on it — `follows` is the column that settles whether removing it
  cost anything. Derived from the caption text, never hand-set, so it can never drift from reality.
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
- The theme of the verse a commenter replied to comes from **`metrics.json`**, not from a
  `posted_media` ledger. (There was one; it never populated. It was written in `daily_post.py`'s
  publish block, but the workflow runs `daily_post.py --emit`, which returns before it — the real
  publish happens in the workflow's `post_instagram.py` step. Anything that must be recorded at
  publish time has to hang off **that** step, not off `daily_post.py`.)
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
  re-sees every comment on every run. Our own hashtag comment is skipped by username.
- **The @handle is never hardcoded.** It is resolved from the API (`post_instagram.username()`),
  cached, and the pass is skipped entirely if it cannot be determined — replying to ourselves is
  worse than not replying. A constant here does not fail loudly when the account is renamed; it
  just makes the account answer its own hashtag comment 🙏 twice a day. (The 2026-08-13 rename
  to @saintseoul_studio is what surfaced this. `IG_USER_ID` is numeric and rename-proof.) (Named
  apart from 10b's `replied_comments` on purpose: one records a public reply, the other a DM,
  and a shared name across two files would eventually get them confused.)
- **No backlog burst.** A comment already older than 24h when first seen is marked handled
  *without* replying: a first deploy answering months of comments at once is precisely the bot
  behaviour the delay exists to prevent.
- Polled every 10 minutes by `.github/workflows/comment-reply.yml`. GitHub's scheduler drifts
  (see rule 1), so the ~30 min target is best-effort, never a guarantee.

## 10d. A published post must never be lost, and must never be published twice
- **Instagram is the source of truth, not the local ledger.** `daily_post.published_refs()` reads
  the account's own captions before picking a verse, so a ledger that failed to save cannot cause
  a repeat. The ledger is an optimisation; the account is the record.
- **The ledger save must survive concurrent bots.** `state.json` / `metrics.json` are single-line
  machine-written JSON and several workflows push them. `git pull --rebase` conflicts on that one
  line; `|| true` then hid it, left the repo mid-rebase and the push died — **after the post had
  already gone out.** `ledger_merge.py` resolves them semantically (dict union, list union,
  counters take max) and the step retries 5× with `if: always()`.
- **One slot, one post.** Hourly crons across a 5-hour lead window; a run claims the slot only
  inside `(0, CLAIM_WINDOW_MIN]` minutes before target, which with hourly spacing is provably
  exactly one run. `--catchup` on the last cron posts late only when the whole chain fired late
  (`CATCHUP_AFTER_MIN`). `slot_already_filled()` asks Instagram as the final backstop.
- **Why this is a content rule and not an ops detail:** on 2026-08-26 the ledger was lost, 잠언
  18:10 went out again on 08-28 and 잠언 27:17 twice on 08-29. Reach fell from ~350 views to ~50
  and did not recover, because Meta demotes repeated/unoriginal content at the ACCOUNT level, not
  the post level. A duplicate is not a cosmetic slip — it is the most expensive defect this
  pipeline can ship.

## 11. No-repeat ledgers (all in `state.json`, committed back after each run)
`used_verses`, `used_music`, `used_scene_cats`, `scene_i`, `post_i`, `music_i`, `used_photos`,
`used_clips`, `posted_media` (media id → theme, for 10b), `replied_comments` (10b, DMs), `dm_i`.
Every rotating resource has a ledger and cycles the whole set before repeating. Perceived sameness counts as a repeat, not just literal file reuse.

**Ledgers that live in their own files, on purpose:** `comments.json` (`replied_publicly`,
`pending_replies`, `reply_i` — rule 10c) and `metrics.json` (rule 11b). Both are written by jobs
that run on a different clock from the poster, and two jobs rebasing the same one-line
`state.json` is a merge conflict waiting to happen. Separate files never collide.

## 11b. Performance ledger — decisions must be measurable (`metrics.json`)
- Every no-repeat ledger above answers *"what have we used?"*. None answers *"did it work?"*, so
  without this file every format argument is taste versus taste. `metrics.py` records one entry
  per published post: the **inputs we chose** (verse, theme, reel duration, Veo segment count)
  next to the **outcome Instagram reports** (reach, plays, shares, saves, watch time).
- Recording inputs beside outcomes is the point — it makes a change measurable *after the fact*
  without an A/B harness. `python3 metrics.py report` groups by reel length and by theme.
- **Separate from `state.json` on purpose.** `state.json` is a bounded, rewritten-every-run
  no-repeat ledger; this is append-only history that must grow. Mixing them would force a choice
  between truncating history and bloating the hot file.
- **Reach is the denominator.** The open question is *why so few people see this*; a share rate
  computed against a tiny reach says nothing about reach itself.
- Insights are **re-pulled** for `MATURE_DAYS` (14) after publishing — reels accrue views for
  well over a week, so a single fetch at publish time would record a near-zero and freeze it.
- Needs `instagram_manage_insights` on the token. Measurement is **`continue-on-error`** in the
  workflow and `insights()` returns `{}` rather than raising: a metrics failure must never take
  down a posting run.
- **`metrics.json` is the one performance ledger.** `insights.py` (added 2026-08-05, before this
  branch was recovered) solved the same problem a second way; it is kept only as the **collector
  for the whole back-catalogue and the follower curve**, writing into this same file. Two ledgers
  measuring one account is how you get two different answers to one question.

## 12. Fallback chain (stay alive, always on-brand)
- Image gen down → licensed photo pool (`used_photos` ledger).
- Veo down / too fast → calm still zoom (24s).
- Lyria down → vetted music library (no-repeat).
None of the fallbacks may violate rules 2–10.

## 12a. The scene pool must last as long as the verse pool
- 36 themes / 72 sentences meant the **same scene description returned every 36 days** while the
  verse pool now runs a year. Images are regenerated each time so no file is ever reused, but the
  same prompt twice in five weeks produces two frames that read as the same post — and this account
  is already under a reach restriction for repeated content.
- Expanded 2026-09-06 to **76 themes / 152 sentences (76 days)**, weighted toward the everyday:
  a cup, an open book, folded linen, shoes by a door, a sparrow on a rail. @dailymayim (34k
  followers, bio 일상에 흐르는 하나님 말씀) is built on ordinary objects rather than landscapes,
  and that is where our pool was thinnest — 8 interiors against 64 landscapes.
- **Adding an interior scene means adding it to `INTERIOR_CATS` in the same change.** Rule 4 spells
  out why: without it the composition instruction asks a kitchen table for "a clear cloudless sky"
  in the upper half and the model paints one above the room.
- Still short of the verse pool's year. Grow it further before growing anything else.

## 12b. The verse pool — verbatim, and large enough that it never wraps
- **개역개정, exactly as printed.** No trimming, no joining, no smoothing, no modernising. On
  2026-09-06 an audit against the full text found **27 of the old 98 were not 개역개정**: 잠언
  19:21 read 굳게 where the text reads 완전히, 시편 34:18 had 충심으로 deleted from the middle of
  the sentence, 예레미야 29:11 was reworded. They had been presented as 개역개정 for months. For a
  Bible account, misquoting scripture is a worse failure than any reach problem.
- **verses.json is generated, never hand-edited.** `build_verses.py` selects from the full text and
  the `Rebuild the verse pool` workflow writes the file. Hand-editing is what produced the 27.
- **The pool must outlast the account's memory.** 98 verses at two posts a day wrapped every 49
  days, so captions repeated word-for-word every seven weeks. Instagram flagged ten of those
  repeats as 퍼온 콘텐츠 and restricted the account's reach: it stopped being recommended to
  non-followers, and views fell from ~350 to ~50. **Pool size is a content rule, not a nicety** —
  keep it big enough that no verse returns inside a year.
- **Selection excludes what a morning verse cannot be:** the law and chronicle books, 욥기 (most of
  it is his friends being wrong, quoted accurately), judgment oracles, imprecatory prayers,
  narrative fragments, and anything needing a name or an event to make sense.
- **A lexicon proposes; a judge decides.** Keywords cannot tell a promise from an oracle — 시편
  69:22 ("그들의 평안이 덫이 되게 하소서") scores as 평안 — so every candidate is judged
  individually for whether it stands alone, the same way renders pass the composition gate. A
  batch that errors is dropped whole: an unverified verse never enters the pool.

## 13. Reading the numbers back — tokens, backfill, degradation
Rule 11b defines the ledger. This rule is about *getting the numbers into it*.

- **`metrics.py` records at publish time; `insights.py` backfills and tracks followers.**
  `insights.py` exists for two gaps only: the ~100 posts published before 11b existed have no
  entry, and nothing else records the follower count. It **does not re-implement metric
  fetching** — `post_instagram.insights()` already degrades tier by tier, and two collectors
  measuring one account is how you get two different answers to one question.
- **Old posts join by verse reference.** The caption carries `[book chapter:verse]`, so posts
  published long before any bookkeeping existed still resolve to a theme via `verses.json`.
- **Two tokens, on purpose.** `IG_ACCESS_TOKEN` is a Facebook-login **system-user** token: it
  never expires and it publishes. It cannot be granted `instagram_manage_insights` without a
  Business-Manager action gated behind SMS 2FA on a phone number that cannot receive Meta's
  codes. `IG_INSIGHTS_TOKEN` comes from **Instagram Login** (`ig_login.py`), needs no Facebook
  account or Page at all, and is **read-only**. `insights.api()` prefers it and reads from
  `graph.instagram.com`; publishing never touches it. **Never replace the publishing token with
  it** — the thing that works must keep working.
- **The 60-day expiry is a machine's problem, not a human's.** Instagram-login tokens last 60
  days and each refresh resets that to 60, so `refresh-token.yml` refreshes **weekly** — eight
  chances to fail before anything expires — and opens an issue if it fails (rule 1: never
  silent). It **skips quietly when the token was never set up**, or it would file that issue
  every Monday. The refreshed token is written to a file and masked, never printed: a token in
  a CI log is a leaked token.
- **Degrade, don't stop.** With no insights scope there is no reach and no shares, so
  `metrics.report()` falls back to `like_count`/`comments_count` — plain media fields needing
  only `instagram_basic` — and **says which mode it is in**. A table that silently changed what
  it ranks by would be worse than no table.
- **Compare like with like.** Engagement tracks how many followers existed at the time, so the
  degraded theme table looks only at the last `THEME_WINDOW` posts. Ranked over all time, 위로
  looked like the worst theme by half; twelve of its thirteen posts were from the account's
  first six days, and the one posted since was above average. Comparing across account sizes
  measures age, not content.

---

### Governance
On **every** update to the pipeline, re-read this file and confirm each rule still holds. Update this
file in the same change whenever a rule intentionally changes, so it never drifts from the code.
