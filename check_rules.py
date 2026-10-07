#!/usr/bin/env python3
"""Check that RULES.md still describes what the code actually does.

A rule written down but not enforced is worse than no rule: it reads as a guarantee. Run this
after touching the pipeline, and add a check here whenever a rule is added to RULES.md.
"""
import json
import os
import pathlib
import re
import sys

import daily_post
import fetch_higgsfield as hf
import generate

HERE = pathlib.Path(__file__).parent


def checks():
    gate = hf._CHECK_PROMPT.lower()
    import content_law
    notext = content_law.LAW.lower()
    daily = (HERE / ".github/workflows/daily-post.yml").read_text()
    daily_post_src = (HERE / "daily_post.py").read_text()
    carousel_wf = (HERE / ".github/workflows/weekly-carousel.yml").read_text()
    carousel = (HERE / "carousel_post.py").read_text()
    scenes = [s for items in hf.SCENE_GROUPS.values() for s in items]
    verses = json.load(open(HERE / "verses.json"))["verses"]

    # The four laws exist once, in content_law.LAW, and BOTH prompts must carry them. Asserting it
    # here is the point: the video prompt went months without any of them.
    law = content_law.LAW
    framing = hf.OUTDOOR_TOP + " " + hf.INDOOR_TOP
    img = content_law.for_image("scene", "look", "framing")
    vid = content_law.for_video("motion")
    for n, marker in ((1, "NO WRITING"), (2, "NO PEOPLE"),
                      (3, "REAL THINGS ONLY"), (4, "FILMED, NOT MADE")):
        yield f"A law {n} is in the image prompt", marker in img
        yield f"A law {n} is in the video prompt", marker in vid
    yield "A laws apply to every frame of the video", "EVERY FRAME" in vid
    yield "A law 2 covers parts of a person", all(
        w in law for w in ("hand", "limb", "silhouette", "reflection of a person"))
    yield "A prohibitions are not duplicated into the framing block", not any(
        w in framing for w in ("CGI", "watermark", "no person"))
    yield "A1 no people (prompt)", "no people" in notext and "silhouette" in notext
    yield "A1 no people (gate)", "any person" in gate
    yield "A2 no writing (prompt)", "no writing" in notext and "watermark" in notext
    yield "A2 no writing (gate)", "any writing" in gate
    yield "A3 no books or paper in any scene", not [
        s for s in scenes if re.search(r"book|\bpaper\b|notebook|envelope", s, re.I)]
    yield "A4 impossible physics (gate)", "vertical mirror" in gate and "stacked duplicate" in gate
    yield "A5 no sky indoors (gate)", "indoor/outdoor composite" in gate
    yield "A6 no CGI look (gate)", "fake / cgi" in gate
    yield "A  the ANIMATION is inspected, not only the still", (
        "clip_survives_inspection" in daily_post_src and "frame_at" in
        (HERE / "make_video.py").read_text())
    # Two frames out of 240 let an arm walk through 예레미야 33:3 (2026-09-25): it arrived after
    # the middle sample and left before the end one. The whole clip is measured, and the moments
    # something entered are inspected too.
    yield "A1b the whole clip is scanned for what entered it", (
        "def intrusion_times" in (HERE / "make_video.py").read_text()
        and "make_video.intrusion_times(clip)" in daily_post_src
        and 'samples.append' in daily_post_src)
    # …but that number may only CHOOSE frames. On the four clips it was built against the bad
    # clip peaked at 3.65 and a clean one at 3.58 — overlapping populations cannot kill a post.
    yield "A1b the intrusion number selects frames, it never rejects", (
        "NOVELTY_PEAK" in daily_post_src
        and '"clip_novelty"' in daily_post_src
        and "if peaks:\n        NOVELTY_PEAK" in daily_post_src
        and "peaks" not in daily_post_src.split("for when, where in samples:")[1][:400])
    # The framing block must not demand a flat plane (that produced the painted panel), and the
    # law must be the thing forbidding one.
    # Every defect the account owner reported must be something the GATE can see, not only
    # something the prompt asks for. Requesting is not checking — that distinction is the whole
    # lesson of 09-14 and 09-17.
    # Calibrated against six real renders the account owner judged by eye (2026-09-19): the two they
    # called split are rejected, the four they accepted pass. Plausibility is explicitly not the
    # test — a real painted dado still halves the frame.
    yield "A2c the gate rejects a line that halves the frame", (
        "cuts the frame in two" in gate.lower()
        and "plausibility is not the test" in gate.lower())
    # Assembled prompts must not contradict themselves. The interior prompt carried both
    # "there is NO horizon" and "One horizon only".
    yield "A2d interior framing is self-consistent", "horizon LOW" not in hf.INDOOR_TOP
    # The scene sentence is the only thing that names objects; the framing must not inject any.
    yield "A2e framing names no objects of its own", not any(
        w in framing for w in ("furniture", "flowers", "rooftops", "the bed", "the lamp"))
    yield "A2b framing does not demand a flat plane", all(
        w not in framing for w in ("FLAT EVEN TONE", "unbroken colour", "NO texture"))
    # The framing must not describe the frame as zones at all — asking for an upper half that
    # holds the verse IS a two-zone composition, and the band is what that description produces.
    yield "A2g framing describes a photograph, not a layout", all(
        w not in framing for w in ("UPPER HALF", "the verse", "panel", "band", "zone"))
    # Interiors must never cluster and must not get the darkest light — a week of dim bare walls
    # is what the account owner saw on 2026-09-19.
    run = best = 0
    for cat in hf.SCENE_CATS:
        run = run + 1 if cat in hf.INTERIOR_CATS else 0
        best = max(best, run)
    yield "A3 interiors never run back to back", best <= 1
    yield "A3 interiors skip the darkest light", (
        hf.INDOOR_LIGHT_CUTOFF < len(hf.LIGHT)
        and "after dark" not in " ".join(hf.LIGHT[:hf.INDOOR_LIGHT_CUTOFF]))
    yield "A2h interior framing has no horizon and no sky above the room", (
        "no sky, no horizon" in hf.INDOOR_TOP and "the room's own wall" in hf.INDOOR_TOP)
    yield "A2b the law forbids a pasted panel and a hard seam", (
        "panel, band or backdrop" in law and "straight edge cutting it into zones" in law)
    gen = (HERE / "generate.py").read_text()
    yield "F5 exactly two type sizes", "SMALL_RATIO" in gen and "MAX_LINES_AT_FULL" in gen
    # Dark is allowed and must stay allowed — three of the seven light phrases are after sunset,
    # and the gate is told explicitly not to flag dark or moody light. What is banned is the
    # feeling, not the light level.
    yield "A7 dark light stays allowed", (
        "dark or moody light" in gate
        and any("after dark" in l for l in hf.LIGHT)
        and "dim is fine" in hf.QUALITY)
    yield "A7 dread is still banned", all(
        w in hf.QUALITY for w in ("gloomy", "ominous", "bleak"))
    yield "A  a rejected render retries on a different scene", "index + a - 1" in (
        HERE / "fetch_higgsfield.py").read_text()
    yield "B1 verses are verbatim (generated, not hand-written)", (HERE / "build_verses.py").exists()
    yield "B3 pool lasts a year at 2/day", len(verses) / 2 > 330
    yield "C2 reel queue", "concurrency:" in daily
    yield "C2b a late run needs evidence, not a schedule argument", (
        'slot_state' in daily_post_src and '"unknown"' in daily_post_src
        and "LATE_LIMIT_MIN" in daily_post_src)
    yield "C2 carousel queue", "concurrency:" in carousel_wf
    yield "C3 slot re-checked just before publishing", "Re-check the slot right before" in daily
    yield "C4 Instagram is the source of truth", hasattr(daily_post, "published_refs")
    yield "C5 ledger saves under if:always with semantic merge", (
        "if: always()" in daily and (HERE / "ledger_merge.py").exists())
    yield "C6 oldest-first (reel)", hasattr(daily_post, "last_published")
    import metrics as _m
    yield "C4b deletions come from the account, since the merge cannot express one", (
        hasattr(_m, "prune_deleted")
        and "prune_deleted" in (HERE / "insights.py").read_text())
    yield "C6 oldest-first (carousel)", "last_published" in carousel
    # C7 — the ledger must be rebuilt from BOTH sources on every run, and a verse that has ever
    # been published must be excluded rather than merely sorted last. 62 ledger entries against
    # 166 published posts is how 47 verses went out twice.
    dp = (HERE / "daily_post.py").read_text()
    yield "C7 ledger rebuilt from Instagram AND metrics.json", (
        "published_refs() + sorted(ago)" in dp)
    yield "C7 an already-published verse is excluded (carousel)", (
        'cand["ref"] not in ago' in carousel)
    state_refs = set(json.loads((HERE / "state.json").read_text()).get("used_verses", []))
    ever = {(e.get("ref") or "").strip()
            for e in json.loads((HERE / "metrics.json").read_text()).values()}
    yield "C7 the ledger knows every verse already published", not (ever - {""}) - state_refs
    yield "D  every INTERIOR_CATS entry is a real scene", not [
        c for c in hf.INTERIOR_CATS if c not in hf.SCENE_GROUPS]
    yield "D  no interior is asked for a sky", not [
        i for i in range(len(hf.SCENES))
        if hf.SCENE_CATS[i] in hf.INTERIOR_CATS
        and 'cloudless sky' in hf.OUTDOOR_TOP]
    yield "F3 text area is measured, not assumed", hasattr(generate, "text_area_ok")
    # F2c — the clearance threshold must be relative to the picture, never an absolute edge value.
    # It was absolute (4.0) for a fortnight and rejected every render it ever saw: four CI logs,
    # 25 renders, six scene families, all reporting -0.0%. A number that cannot vary is not a
    # measurement. The property, not the constant, is what is enforced here.
    yield "F2c clearance is measured against the picture's own busyness", (
        hasattr(hf, "CLEAR_RISE") and 0.0 < hf.CLEAR_RISE < 1.0
        and "quiet + CLEAR_RISE" in (HERE / "fetch_higgsfield.py").read_text())
    # …and the quiet reference must be read from above the verse block (25.6%), so the number does
    # not change depending on whether text has been composited.
    yield "F2c the quiet reference is read above the verse block", (
        "int(h * 0.20)" in (HERE / "fetch_higgsfield.py").read_text())
    # A5b — the seam gate must be MEASURED and must run even when the model said yes, because on
    # 2026-09-14 the model said yes to a stacked composite and it shipped.
    yield "A5b stacked composites are measured, not asked about", hasattr(hf, "has_seam")
    yield "A5b the seam gate runs even when the model approves", (
        "if ok and has_seam(dest)" in (HERE / "fetch_higgsfield.py").read_text())
    yield "A5b both thresholds must trip", (
        hf.SEAM_JUMP >= 5.0 and hf.SEAM_RATIO >= 20.0)
    # F2a — seam_score is blind between 18% and 45% of the height, which is exactly where
    # OUTDOOR_TOP asks the sky to end. 디모데전서 2:4 (2026-10-06) shipped a forest cut off at
    # 32.1% and has_seam reported ok. A second gate covers that band by measuring STRAIGHTNESS.
    yield "F2a a ruled line across the top is measured", hasattr(hf, "has_ruled_line")
    yield "F2a the ruled-line gate runs even when the model approves", (
        "if ok and has_ruled_line(dest)" in (HERE / "fetch_higgsfield.py").read_text())
    # The window has to still cover the band seam_score skips, or the blind spot is back.
    yield "F2a the ruled-line window covers seam_score's blind band", (
        hf.RULED_FROM <= 0.18 and hf.RULED_UPTO >= 0.40)
    # Calibrated 0.900 (defect) against 0.347 (worst clean) over 29 published reels. A limit
    # outside this range has stopped being the measurement it claims to be.
    yield "F2a the ruled-line limit sits between the measured groups", (
        0.40 <= hf.RULED_FRAC <= 0.80)
    # Only columns no glyph can reach — col_w never exceeds 0.85 of the frame (generate.py).
    yield "F2a the ruled-line gate samples only glyph-free columns", (
        0 < hf.RULED_MARGIN <= 0.075)
    # F2a-1 — the instruction, not the scene, chose where that line fell. A scene with no horizon
    # must not be told to put one a third of the way up and that nothing may rise into the sky.
    yield "F2a-1 horizonless outdoor scenes are not asked to invent a horizon", (
        "no horizon of its own" in hf.OUTDOOR_TOP
        and "nothing rises into the sky" not in hf.OUTDOOR_TOP)
    # F2a-2 — a scene whose own text says it is inside must not be handed OUTDOOR_TOP.
    yield "F2a-2 scenes that describe an interior are registered as interiors", not [
        hf.SCENE_CATS[i] for i, s in enumerate(hf.SCENES)
        if hf.SCENE_CATS[i] not in hf.INTERIOR_CATS
        and ("interior" in s or "nave" in s or "windowsill" in s)]
    # B5 — the caption line is ON as of 2026-09-14, in BOTH publishing paths. A reflection that
    # reached the reel and not the carousel would leave half the account exactly as unoriginal as
    # before, which is the failure this rule exists to prevent.
    import reflection
    yield "B5 the caption line is enabled (reel)", "CAPTION_REFLECTION" in daily
    yield "B5 the caption line is enabled (carousel)", "CAPTION_REFLECTION" in carousel_wf
    yield "B5 one caption builder for both post types", "build_caption" in carousel
    # …and it must still be unable to break a post: no key, no network, a line that breaks the
    # register — all of those have to end as the verse-only caption rather than an exception.
    os.environ.pop("CAPTION_REFLECTION", None)
    verse = {"text": "여호와는 나의 목자시니 내게 부족함이 없으리로다", "ref": "시편 23:1"}
    plain = f"{verse['text']}\n[{verse['ref']}]"
    yield "B5 a failed reflection still produces a caption", (
        not reflection.enabled()
        # an ordinary date, so the B-5b greeting is not what is being measured here
        and daily_post.build_caption(verse, "", today="2026-01-01") == plain)
    # B5b — the 명절 greeting is CAPTION ONLY, date-gated, and sits under the 출처.
    yield "B5b an unlisted date gets no greeting", (
        daily_post.greeting("2026-03-01") is None
        and daily_post.build_caption(verse, "", today="2026-03-01") == plain)
    chuseok = daily_post.build_caption(verse, "", today="2026-09-25")
    yield "B5b a listed date gets the greeting, below the 출처", (
        daily_post.greeting("2026-09-25") == "풍성한 한가위 보내세요."
        and chuseok.startswith(plain) and chuseok.endswith("풍성한 한가위 보내세요."))
    yield "B5b the greeting never reaches the frame", not any(
        any(g in (HERE / f).read_text() for g in set(daily_post.GREETINGS.values()))
        for f in ("generate.py", "content_law.py", "fetch_veo.py", "fetch_higgsfield.py"))
    yield "B5 the line is one quiet sentence, not a sermon", (
        reflection.MAX_CHARS <= 60 and reflection._clean("오늘도 힘내세요.") is None
        and reflection._clean("이 말씀을 붙들고 오늘을 삽시다.") is None)
    ig = (HERE / "post_instagram.py").read_text()
    yield "H0 API errors carry the API's reason", "detail.get('message')" in ig
    yield "H0b transient publish failures retry", (
        "MediaProcessingError" in ig and "with_retry" in ig)
    # Motion must be measured a second apart, not frame to frame — see RULES.md E2.
    import inspect
    import make_video
    src = inspect.getsource(make_video.motion_score)
    yield "E2 motion measured one second apart", "stride" in src and "fps=" in src
    daily_src = (HERE / "daily_post.py").read_text()
    # motion_score is recorded, never a retry reason — measured 0.0px displacement on clips it
    # was scoring 1.8-8.4, and 0 of 18 first attempts ever cleared its limit.
    yield "E0 veo seconds are recorded so the bill is measured", (
        '"veo_seconds"' in daily_src and hasattr(_m, "spend"))
    yield "E2b motion is recorded, not a reason to regenerate", (
        "RECORDED, never a reason to regenerate" in daily_src)
    yield "E3 gate selects the calmest rather than rejecting", (
        "MOTION_HARD" in daily_src and "MOTION_HARD and sky <= SKY_HARD" in daily_src)
    # Continuations are inspected and retry only on a real defect — they used to take two takes,
    # choose on the motion number, and inspect neither.
    yield "E4 continuations are inspected", "clip_survives_inspection(nxt" in daily_src
    yield "E4 a retry needs a real defect, not a motion number", (
        "if s_ov <= MOTION_MAX" not in daily_src and "VEO_TRIES" in daily_src)
    # 62.7% of the Veo seconds bought after 2026-09-23 were thrown away, and the posts that
    # retried MOST shipped the SHORTEST reels. Both halves of E-0c have to hold or the leak
    # reopens quietly: the chain must not start after a miss, AND a continuation gets one take.
    yield "E0c a continuation gets exactly one take", (
        "CHAIN_TRIES = 1" in daily_src
        and "for attempt in range(1, CHAIN_TRIES + 1)" in daily_src)
    yield "E0c a scene that missed once is not chained at all", (
        "chain_ok = (motion_attempts == 1 and not spoiled)" in daily_src
        and "(SEGMENTS + 1) if chain_ok else 2" in daily_src)
    yield "E0d takes per segment are recorded, not reconstructed", (
        '"veo_attempts"' in daily_src and "veo_attempts.append" in daily_src)
    # G-2. The API refuses insights with (#10), and for two months that was recorded as "we
    # cannot see reach or shares" — while the app showed views, sends and reposts on every post.
    # The ledger must have somewhere to PUT a number read off the screen, sends above all:
    # sends-per-reach is the ranking signal Instagram names out loud, and likes are a proxy.
    yield "G2 shares can be recorded by hand, not just views", (
        "shares" in _m.APP_FIELDS and "reposts" in _m.APP_FIELDS
        and callable(getattr(_m, "note", None)))
    yield "G2 a hand-entered number is marked as one", (
        '_manual' in inspect.getsource(_m.note))
    # A real API answer must clear the marker for the field it answered — a stale shares_manual
    # next to an API shares would make the one ranking number look untrustworthy when it went real.
    yield "G2 an API answer clears the hand-entered marker on every field", (
        "for _f in APP_FIELDS" in inspect.getsource(_m.refresh))
    # G-2.5 The 릴스 인사이트 screen is one tap deeper than the post, and carries the three
    # things this ledger could not hold: reach itself, watch time, and where the views came
    # from. 탐색 탭 is a non-follower surface, so src_* is a direct read on distribution that
    # follower-ratio arithmetic could only infer.
    yield "G2.5 the deeper insights screen has fields to land in", (
        all(f in _m.APP_FIELDS for f in
            ("reach", "watch", "skip_rate", "src_reels", "src_explore", "src_feed", "saves")))
    # G-2.6 The name typed in is the screen's; the name on disk is the API's. When those two
    # drift, the number is recorded and invisible — which happened twice on 2026-10-07.
    yield "G2.6 saves lands in the API's field name, not the app's", (
        _m._stored("saves") == "saved" and _m._stored("watch") == "ig_reels_avg_watch_time"
        # Caught by this very rule hours after it was written: 건너뛰기 비율 was stored as
        # `skip_rate` while the API answers to `reels_skip_rate`, so the hand-entered 85.2%
        # and the first API answer would have landed in two fields that never met.
        and _m._stored("skip_rate") == "reels_skip_rate")
    # G-2.1a The API was never the limit — one permission was missing and nobody asked the
    # token for two months. The diagnosis must be one command, not an argument from memory.
    import ig_doctor
    yield "G2.1a a tool exists that asks the token what it can do", (
        callable(getattr(ig_doctor, "describe", None))
        and "debug_token" in inspect.getsource(ig_doctor.describe))
    yield "G2.1a the doctor names the permission that is actually missing", (
        any("instagram_manage_insights" in need for need in ig_doctor.NEEDED.values())
        and any("instagram_business_manage_insights" in need
                for need in ig_doctor.NEEDED.values()))
    # G-2.1b A (#10) sweep cannot tell a real metric from an invented one — permission is
    # checked before the name is. Whoever reads probe() next has to be told, in the code.
    yield "G2.1b the (#10) trap is written down where it would be re-made", (
        "(#10)" in inspect.getsource(ig_doctor.probe)
        and "view_sources" in inspect.getsource(ig_doctor.probe))
    # G-2.1d A read token is only valid against its own host. Without `base`, an Instagram
    # Login token fails OAuth, insights() returns {}, and the log says "insights unavailable"
    # — identical to having no permission. A human's OAuth trip would have been wasted.
    import post_instagram as _p
    yield "G2.1d insights() is sent to the host its token is valid for", (
        "base" in inspect.signature(_p.insights).parameters
        and "{GRAPH}/" not in inspect.getsource(_p.insights))
    import insights as _i
    yield "G2.1d insights.py hands the base down", (
        "base=base" in inspect.getsource(_i.backfill))
    # The two metrics that were hand-entered while the API had names for them.
    yield "G2.1a reels_skip_rate and reposts are actually requested", (
        {"reels_skip_rate", "reposts"} <= {m for t in _p.INSIGHT_TIERS for m in t}
        and {"reels_skip_rate", "reposts"} <= set(_p.INSIGHT_SINGLES))
    yield "G2.6 the hand-entry marker follows the stored name", (
        "_stored(_f)" in inspect.getsource(_m.refresh)
        and "_stored(k)" in inspect.getsource(_m.note))
    yield "G2.6 a percentage off the screen is not truncated to an int", (
        "_PCT_FIELDS" in inspect.getsource(_m.note) and "float(v)" in inspect.getsource(_m.note))
    # G-2.7 A mean printed under an n=13 header while standing on 1 post is the quiet overclaim
    # this whole ledger exists to stop.
    yield "G2.7 sparse averages in report() carry their own n", (
        "def avg_n" in inspect.getsource(_m.report)
        and "n={len(vals)}" in inspect.getsource(_m.report))
    # ...and the "these rows use views, not reach" note must survive the first real reach,
    # instead of going quiet the moment one post has it.
    yield "G2.7 the views-as-denominator note survives partial reach", (
        "if exact < len(scored)" in inspect.getsource(_m.report))

    # --- G-3 collect everything the docs document; choose later ------------------------------
    import ig_catalog as _c
    import ig_probe as _pr
    # G-3.1 The request list must be DERIVED from the catalog. A hand-typed list at the request
    # site is how `reels_skip_rate` stayed unrequested while being named the #1 problem.
    _psrc = inspect.getsource(_p)
    yield "G3.1 the request bundles are derived from ig_catalog, not hand-typed", (
        "ig_catalog.tiers(" in _psrc
        and _p.INSIGHT_TIERS[0] == _c.tiers(_c.REELS)[0]
        and set(_p.INSIGHT_SINGLES) == (set(_c.media_metrics(_c.REELS, bundle_only=True))
                                        | set(_c.media_metrics(_c.REELS, fragile_only=True))))
    # G-3.2 One throw-prone name in a bundle blanks every other metric in the same request.
    yield "G3.2 no conditional-failure metric rides in any bundle", all(
        not (set(t) & {n for n, s in _c.MEDIA_METRICS.items() if not s["bundle"]})
        for pt in (_c.REELS, _c.FEED, _c.STORY) for t in _c.tiers(pt))
    yield "G3.2 bundles are built per media product type", (
        "product_type" in inspect.signature(_p.insights).parameters
        and set(_c.tiers(_c.FEED)[0]) != set(_c.tiers(_c.REELS)[0]))
    # G-3.3 copyright_check_information fails a whole /media page; it must be fetched alone.
    yield "G3.3 the listing-fatal field is kept out of the batch", (
        _c.MEDIA_FIELDS_SOLO
        and not (set(_c.MEDIA_FIELDS_SOLO) & set(_c.media_fields()))
        and set(_c.MEDIA_FIELDS_SOLO) <= set(_c.media_fields(solo=True)))
    # G-3.4 The plain fields that need no insights scope must actually be requested.
    yield "G3.4 the scope-free count fields are in the listing", (
        {"total_views_count", "shares_count", "reposts_count"} <= set(_c.media_fields()))
    # G-3.5 Provenance written down, never deduced from a missing marker (the likes=2 freeze).
    _isrc = inspect.getsource(_i.backfill)
    yield "G3.5 provenance is read from an explicit marker", (
        '_api' in _isrc and 'FIELD_AS_METRIC_ORDER' in _isrc
        and 'got.get(f"{metric}_api")' in _isrc)
    yield "G3.5 an endpoint answer is marked so a plain field stops overwriting it", (
        "DUAL_SOURCE" in _isrc and "DUAL_SOURCE" in inspect.getsource(_m.refresh))
    # G-3.6 The account dimension, and the breakdown that replaces an inference with a number.
    yield "G3.6 account insights are collected with every documented breakdown", (
        hasattr(_i, "account")
        and ("reach", "follow_type") in {(m, bd) for m, _p2, _t, bd, _tf
                                         in _c.account_requests() if bd})
    yield "G3.6 the account ledger is its own file, keyed by date", (
        _i.ACCOUNT.endswith("account.json") and _i.ACCOUNT != _m.FILE)
    # G-3.7 A refusal and a zero are different facts; the refusal has to be on disk.
    _asrc = inspect.getsource(_i.account)
    yield "G3.7 rejected account metrics are recorded, not just logged", (
        'day["errors"] = errors' in _asrc and 'errors[key] = str(e)' in _asrc)
    yield "G3.7 an all-identical refusal is compressed, a partial one is not", (
        'len(set(errors.values())) == 1 and not ok' in _asrc
        and '"*_requests"' in _asrc)
    yield "G3.7 errors do not accumulate across runs the way values do", (
        "errors = {}" in _asrc and 'day.setdefault("insights"' in _asrc)
    # G-3.8 The probe must say out loud that its ❌ is not evidence a metric is unavailable.
    yield "G3.8 the probe warns that (#10) cannot prove absence", (
        "NOT 'this metric does not exist'" in inspect.getsource(_pr.show))
    import fetch_veo
    yield "E3 retries escalate the demand", (
        len(fetch_veo.CALMER) == 3 and "frozen photograph" in fetch_veo.CALMER[2].lower()
        and daily_src.count("fetch_veo.CALMER[attempt - 1]") == 2)
    yield "E8 shipped motion is recorded", '"motion": round(ov, 3)' in daily_src
    # A gate that silently stopped running must be a number, not a log line. Posts ship with
    # gate_ran / gate_skipped so "was this checked at all" is answerable afterwards.
    yield "H0c a gate that never ran is recorded and warned about", (
        '"gate_ran"' in daily_src and "never reached the model" in daily_src
        and "GATE_RAN" in (HERE / "fetch_higgsfield.py").read_text())
    # The clip inspection must see the RAW Veo output. If it ever ran after the verse was
    # composited it would reject every take for containing writing — verified by measurement.
    yield "A2f clip inspection runs before the verse is composited", (
        daily_src.index("clip_survives_inspection(clip") < daily_src.index("build_reel_native"))
    insights = (HERE / ".github/workflows/insights.yml").read_text()
    yield "G1 alerts only on trouble, not every post", (
        "notify.py --posted" not in daily and "python watch.py" in insights)
    yield "G1 an alert cannot fail a post", (
        "continue-on-error: true" in insights
        and "not configured" in (HERE / "notify.py").read_text())
    watch = (HERE / "watch.py").read_text()
    yield "G1 watcher covers drop, dead and missed slots", (
        '"drop"' in watch and '"dead"' in watch and 'f"missed-' in watch
        and "COOLDOWN_DAYS" in watch)
    yield "G1 missed slots are judged per slot, within GRACE_H", (
        "SLOTS = (5, 19)" in watch and "GRACE_H = 2" in watch)
    yield "G1 missed slots ask Instagram, not the ledger", "published_times" in watch and (
        "post_instagram" in watch)
    yield "G1 the watcher runs often enough to be timely", len(
        [l for l in (HERE / ".github/workflows/watch.yml").read_text().splitlines()
         if "cron:" in l]) >= 4


def main():
    failed = []
    # The env audit is a separate script because it needs a YAML parser; run it here so one
    # command answers "is everything still enforced". Its failure mode — a workflow that does not
    # pass the credentials its code reads — is the most expensive one in this repo, because it
    # fails silently and every guard degrades without saying so.
    import subprocess
    env_ok = subprocess.run([sys.executable, str(HERE / "audit_env.py")],
                            capture_output=True, text=True)
    if env_ok.returncode == 2:
        print(f"  CANNOT VERIFY  workflow env audit — {env_ok.stdout.strip()}")
        failed.append("workflow env audit (could not run)")
    elif env_ok.returncode != 0:
        print(env_ok.stdout)
        failed.append("workflow env audit")
    else:
        print("  PASS  workflow steps pass the env their code reads")
    for name, passed in checks():
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        if not passed:
            failed.append(name)
    print(f"\n{'all rules hold' if not failed else str(len(failed)) + ' RULE(S) NOT ENFORCED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
