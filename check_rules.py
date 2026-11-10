#!/usr/bin/env python3
"""Check that RULES.md still describes what the code actually does.

A rule written down but not enforced is worse than no rule: it reads as a guarantee. Run this
after touching the pipeline, and add a check here whenever a rule is added to RULES.md.
"""
import inspect
import json
import os
import pathlib
import re
import sys

import daily_post
import fetch_image as hf
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
    checks_wf = (HERE / ".github/workflows/checks.yml").read_text()
    verify_sh = (HERE / "verify.sh").read_text()
    import qa_gate
    qa_src = (HERE / "qa_gate.py").read_text()
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
    # Section 0 — the account that must never be touched. Enforced as PRESENCE in both files,
    # because it cannot be enforced in code: nothing in this repo converts an account. What it
    # guards against is a button being clicked, so the rule has to sit where it is read first.
    rules_md = (HERE / "RULES.md").read_text()
    claude_md = (HERE / "CLAUDE.md").read_text()
    yield "0-1 wonsukwaynelee is named as never-touch in RULES.md", (
        "wonsukwaynelee" in rules_md and "되돌릴 수 없" in rules_md)
    yield "0-1 and in CLAUDE.md, ahead of the pipeline instructions", (
        "wonsukwaynelee" in claude_md
        and claude_md.index("wonsukwaynelee") < claude_md.index("read [RULES.md]"))
    dp = (HERE / "daily_post.py").read_text()
    wt = (HERE / "watch.py").read_text()
    # C4f — the weekly carousel is a FEED post and must not fill a daily reel slot.
    yield "C4f daily_post counts only reels for a slot", (
        'media_product_type") != "REELS"' in dp)
    yield "C4g a rejected picture shipping is announced too", (
        "def unchecked_run" in wt and '_tail_run("gate_passed", False)' in wt)
    yield "C4g motion loss alerts before a week of stills", (
        "MOTION_DEAD_RUN" in wt and "def still_run" in wt)
    yield "C4f the half-day test has one implementation per path", (
        wt.count("timedelta(hours=12)") == 1)
    yield "C4f the watcher counts only reels too", (
        'media_product_type") != "REELS"' in wt)
    # C4i — Instagram FETCHES our media by URL, so the 30-asset retention must keep the
    # NEWEST uploads, not the lexicographically largest NAMES. `carousel-*` sorts below every
    # `post-*`, so a name sort put seconds-old carousel slides in the delete set every time.
    # Comment lines are stripped first: the retired expression is quoted in the comment that
    # explains why it was retired, and twice now a check has tripped over its own explanation.
    _daily_code = "\n".join(l for l in daily.splitlines() if not l.strip().startswith("#"))
    yield "C4i the release prune keeps the newest by upload time, not by name", (
        "sort_by(.createdAt)" in _daily_code
        and "'.assets[].name' | sort" not in _daily_code)
    gen = (HERE / "generate.py").read_text()
    # F-2b: one type size, and the two numbers that make it possible. The 35px fallback stays
    # in the code as a net, but every verse we ship must clear the bar at full size.
    yield "F2b tracking and set width are set", (
        "TRACK = -0.05" in gen and "WIDTH = 0.80" in gen)
    # F-4a/4b: tears are ranked, and the noun rule reads the next word's HEAD.
    yield "F4-1 boundaries are graded, not a yes/no clause test", (
        "def boundary" in gen and "P_STEP" in gen and "is_clause_end" not in gen)
    yield "F4-2 only auxiliary connectives chain to the next verb", (
        "_AUX_EC and finite_predicate" in gen)
    yield "F4-5 predicate detection reads every morpheme", (
        "def _word_is_predicate" in gen and "def _is_verb" in gen
        and 'tag.split("-")[0]' in gen)
    yield "F4-6 the 것이나 mis-tag is corrected at source", (
        'tag == "JC" and form == "이나"' in gen)
    tracking_test = (HERE / "test_tracking.py").read_text()
    yield "F4-A the per-line character capacity is pinned by a test", (
        "WidthIsComputableNotJustMeasurable" in tracking_test)
    # 2026-11-09: this test hardcoded HANGUL = 42.0 — a value measured once on a developer's
    # macOS machine. CI (Ubuntu, FreeType 2.14.3) renders the same font 0.1875px narrower, so
    # the hardcoded test failed on every single CI run from the day it was written (2026-10-19)
    # until this was found, 19 days of red builds nobody looked at because checks.yml had no
    # notify path yet (see J-2). The constant must be measured live, like every other number in
    # this file already is (`generate.verse_col_w`, never retyped) — not pinned to one platform's
    # font renderer and asserted true for all of them.
    yield "F4-A the Hangul width constant is measured live, not re-hardcoded per platform", (
        "cls.HANGUL = font.getlength(" in tracking_test
        and re.search(r"HANGUL\s*=\s*[\d.]+", tracking_test) is None)
    yield "F4-7 a clause-boundary break is free", (
        "max(0, 3 - boundary(b))" in gen)
    yield "F4-8 one line needs one clause, not just a short verse", (
        "one_line_ok" in gen and "boundary(i) >= 3" in gen)
    yield "F4a tears are ranked, not one flat penalty", (
        "TEAR_PHRASE" in gen and "TEAR_CLAUSE" in gen
        and "P_FORBID" not in gen)
    yield "F4b the bare-noun rule reads the next word's head", (
        'head_tag(i + 1) in ("NNG", "NNP")' in gen)
    yield "F2b the verse column is named, not retyped", (
        "REEL_COL = 0.68" in gen and "def verse_col_w" in gen
        and "0.68 if canvas" not in gen)
    yield "F2b three lines at full size, never four", ("MAX_LINES_AT_FULL = 3" in gen)
    yield "F2b measuring and drawing read the same two numbers", (
        "def text_w" in gen and "def draw_text" in gen
        and gen.count("_tracked()") >= 3)
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
        HERE / "fetch_image.py").read_text()
    yield "B1 verses are verbatim (generated, not hand-written)", (HERE / "build_verses.py").exists()
    yield "B3 pool lasts a year at 2/day", len(verses) / 2 > 330
    yield "C2 reel queue", "concurrency:" in daily
    # 2026-11-10: the 5-cron-per-slot chain (wait/jitter/claim-window) was removed — one cron per
    # slot now, post the moment it fires. Guard against the chain quietly growing back: exactly
    # one `cron:` line per slot, and no leftover wait/jitter machinery in daily_post.py.
    yield "C2b exactly one cron per slot, no chain", daily.count("- cron:") == 2
    yield "C2b no in-job wait/jitter left to drift out of sync", (
        "wait_until_target" not in daily_post_src
        and "CLAIM_WINDOW_MIN" not in daily_post_src
        and "time.sleep" not in daily_post_src)
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
    # C4c/C4d/C4e — the three halves that were missing. A pruned row used to be destroyed rather
    # than moved, the removal was handed straight back by the next merge, and the verse stayed
    # blocked for a full cycle (고린도전서 15:55 had to be released by hand on 09-22).
    _met = (HERE / "metrics.py").read_text()
    yield "C4c a deleted post's measurements are archived, not destroyed", (
        hasattr(_m, "load_deleted") and "metrics_deleted.json" in _met
        and "deleted_noticed" in _met)
    yield "C4c nothing is pruned when it cannot be archived", (
        "the deleted-post archive is unreadable" in _met)
    yield "C4d a resurrected row is dropped on sight at every read", (
        hasattr(_m, "_drop_resurrected") and "_drop_resurrected(json.load(f))" in _met)
    yield "C4d the archive is saved by the workflow that writes it", (
        "metrics_deleted.json" in (HERE / ".github/workflows/insights.yml").read_text())
    yield "C4e a deleted post's verse is released from used_verses", (
        hasattr(_m, "release_verses")
        and "state.json" in _met and "used_verses" in _met)
    yield "C4e the release is recomputed from the archive every run, not once", (
        'release_verses([e.get("ref") for e in archive.values()]' in _met)
    yield "C4e a verse another live post still holds is not released", (
        "still_used" in _met and "live_refs" in _met)
    yield "C4e the released state.json is saved by that workflow too", (
        "state.json" in (HERE / ".github/workflows/insights.yml").read_text())
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
    # D-1 (2026-11-04): SCENE_STRUCTURE must cover every SCENE_GROUPS key exactly, both
    # directions — a scene family registered on only one side is a family pick_scene's structural
    # check cannot see, which is precisely how the room/water/field clustering happened.
    yield "D-1 every SCENE_GROUPS key has a structural bucket", (
        set(hf.SCENE_GROUPS) <= set(hf.SCENE_STRUCTURE))
    yield "D-1 SCENE_STRUCTURE has no stray keys outside SCENE_GROUPS", (
        set(hf.SCENE_STRUCTURE) <= set(hf.SCENE_GROUPS))
    yield "D-1 pick_scene avoids the recent structural bucket by default", (
        "avoid_structure" in inspect.signature(hf.pick_scene).parameters
        and inspect.signature(hf.pick_scene).parameters["avoid_structure"].default > 0)
    # D-2 (2026-11-04): the biweekly reference-study bot exists, is wired to a cron, has at least
    # one account configured, and — the actual promise in RULES.md D-2 — never writes to
    # fetch_image.py. A script that can edit the prompt pool for itself is not "suggestions for
    # review" no matter what its docstring claims.
    import reference_study as _rs
    yield "D-2 reference_study has at least one account configured", bool(_rs.REFERENCE_ACCOUNTS)
    yield "D-2 reference_study never opens fetch_image.py for writing", not any(
        tok in (HERE / "reference_study.py").read_text()
        for tok in ('open("fetch_image.py", "w"', "open('fetch_image.py', 'w'",
                    'fetch_image.py", "a"', "fetch_image.py', 'a'"))
    ref_wf = (HERE / ".github/workflows/reference-study.yml")
    yield "D-2 the reference-study workflow exists and is on a cron", (
        ref_wf.exists() and "cron:" in ref_wf.read_text())
    yield "D-2 the ledger is saved with the one shared implementation (H0-4)", (
        "save_ledger.sh" in ref_wf.read_text())
    # D-3 (2026-11-08): ledger_merge.py's generic int-max/list-union rule froze state.json's
    # scene_i/used_scene_cats in production for weeks — D-1's whole defense was silently deciding
    # nothing. These two keys must be whole-value OURS-wins, and the OTHER counters/lists this
    # file exists to protect (post_i, used_verses, ...) must NOT have been swept in with them.
    import ledger_merge as _lm
    yield "D-3 scene_i and used_scene_cats are ours-wins, not max()/union", (
        {"scene_i", "used_scene_cats"} <= _lm.OURS_REPLACES_KEYS)
    yield "D-3 genuinely monotonic/cumulative ledgers were not swept in by mistake", not (
        _lm.OURS_REPLACES_KEYS & {"post_i", "music_i", "used_verses", "used_clips", "used_photos"})
    yield "D-3 watch.py has a frozen-ledger detector wired into findings()", (
        "def scene_fingerprint" in wt and '"scene-frozen"' in wt
        and "_scene_watch" in wt)
    # D-3b (2026-11-10): OURS_REPLACES_KEYS only fires while walking ours.items(), so a key OURS
    # dropped (rather than changed) was never visited and theirs's stale copy survived forever —
    # account.json's `errors`, which insights.account() deliberately removes once a run has none,
    # kept a lunchtime-fixed rejection alive next to the same day's working metrics. `errors` needs
    # BOTH sets: present -> replace (not union, or a fixed error reappears beside a real one),
    # absent -> delete.
    yield "D-3b errors is both ours-wins and delete-when-absent", (
        "errors" in _lm.OURS_REPLACES_KEYS and "errors" in _lm.OURS_OMITS_DELETES)
    yield "D-3b merge() actually applies OURS_OMITS_DELETES, not just defines it", (
        "OURS_OMITS_DELETES" in inspect.getsource(_lm.merge))
    yield "F3 text area is measured, not assumed", hasattr(generate, "text_area_ok")
    # F2c — the clearance threshold must be relative to the picture, never an absolute edge value.
    # It was absolute (4.0) for a fortnight and rejected every render it ever saw: four CI logs,
    # 25 renders, six scene families, all reporting -0.0%. A number that cannot vary is not a
    # measurement. The property, not the constant, is what is enforced here.
    yield "F2c clearance is measured against the picture's own busyness", (
        hasattr(hf, "CLEAR_RISE") and 0.0 < hf.CLEAR_RISE < 1.0
        and "quiet + CLEAR_RISE" in (HERE / "fetch_image.py").read_text())
    # …and the quiet reference must be read from above the verse block (25.6%), so the number does
    # not change depending on whether text has been composited.
    yield "F2c the quiet reference is read above the verse block", (
        "int(h * 0.20)" in (HERE / "fetch_image.py").read_text())
    # A5b — the seam gate must be MEASURED and must run even when the model said yes, because on
    # 2026-09-14 the model said yes to a stacked composite and it shipped.
    yield "A5b stacked composites are measured, not asked about", hasattr(hf, "has_seam")
    yield "A5b the seam gate runs even when the model approves", (
        "if ok and has_seam(dest)" in (HERE / "fetch_image.py").read_text())
    yield "A5b both thresholds must trip", (
        hf.SEAM_JUMP >= 5.0 and hf.SEAM_RATIO >= 20.0)
    # F2a — seam_score is blind between 18% and 45% of the height, which is exactly where
    # OUTDOOR_TOP asks the sky to end. 디모데전서 2:4 (2026-10-06) shipped a forest cut off at
    # 32.1% and has_seam reported ok. A second gate covers that band by measuring STRAIGHTNESS.
    yield "F2a a ruled line across the top is measured", hasattr(hf, "has_ruled_line")
    yield "F2a the ruled-line gate runs even when the model approves", (
        "if ok and has_ruled_line(dest)" in (HERE / "fetch_image.py").read_text())
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
        for f in ("generate.py", "content_law.py", "fetch_motion.py", "fetch_image.py"))
    yield "B5 the line is one quiet sentence, not a sermon", (
        reflection.MAX_CHARS <= 60 and reflection._clean("오늘도 힘내세요.") is None
        and reflection._clean("이 말씀을 붙들고 오늘을 삽시다.") is None)
    ig = (HERE / "post_instagram.py").read_text()
    # This used to just grep the whole file for "detail.get('message')" — true because _get had
    # it, blind to the fact _post never did. _post's missing unwrap is exactly how 2026-11-08's
    # weekly-carousel publish failure logged nothing but "HTTP Error 400: Bad Request" with
    # Meta's real reason thrown away. So: both _get and _post must route through the ONE place
    # that unwraps an HTTPError body (_open), and neither may call urlopen directly — otherwise a
    # third call site could reintroduce the same gap with the grep still passing.
    import post_instagram as pi
    open_src = inspect.getsource(pi._open)
    get_src = inspect.getsource(pi._get)
    post_src = inspect.getsource(pi._post)
    yield "H0 the one error-unwrap implementation reads the API's reason", (
        "detail.get('message')" in open_src)
    yield "H0 _get routes through it, not a raw urlopen", (
        "_open(" in get_src and "urlopen" not in get_src)
    # Checking _get and _post BY NAME is exactly what let _post go a month without this fix —
    # the old check passed with _post completely unguarded because it never looked at _post at
    # all. This closes the gap the comment above actually claims to close: count every call to
    # urlopen( in the WHOLE file and require all of them to live inside _open's own source, so a
    # future _delete()/_patch() written the old way (raw urlopen, no unwrap) fails this check
    # even though it has a name this file has never heard of.
    yield "H0 urlopen() is called nowhere in this file except inside _open", (
        ig.count("urlopen(") == open_src.count("urlopen(") > 0)
    yield "H0 _post routes through it too, not a raw urlopen", (
        "_open(" in post_src and "urlopen" not in post_src)
    yield "H0b transient publish failures retry", (
        "MediaProcessingError" in ig and "with_retry" in ig)
    # Motion must be measured a second apart, not frame to frame — see RULES.md E2.
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
    # E-0c was "a scene that missed once is not chained", which capped cost by making the reel
    # short — and 52% came out at 7.7s, looping four times under the hymn. Length is uniform now
    # and the ceiling is held by arithmetic instead: VEO_TRIES + (SEGMENTS-1)*CHAIN_TRIES calls
    # must fit the Veo budget. test_veo_budget.py checks the won; this checks the shape.
    _vt = int(re.search(r"VEO_TRIES = (\d+)", daily_src).group(1))
    _ct = int(re.search(r"CHAIN_TRIES = (\d+)", daily_src).group(1))
    import daily_post as _dp
    yield "E0c every reel is the same length", "if chain_ok else 2" not in daily_src
    yield "E0c the worst case fits three Veo calls", _vt + (_dp.SEGMENTS - 1) * _ct <= 3
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
    # G-2.1e: the same host-mismatch trap as G-2.1d, one layer down. recent_media() hardcoded
    # graph.facebook.com regardless of the base insights.api() resolved, so an IG_INSIGHTS_TOKEN
    # call through prune_deleted() got a generic "cannot parse access token" (code 190) that
    # read exactly like a malformed token rather than a wrong host — and the except-and-log in
    # prune_deleted swallowed it into "prune skipped", indistinguishable from nothing to prune.
    # Found live 2026-11-10 (run 42736744636) the day IG_INSIGHTS_TOKEN first won api()'s choice.
    yield "G2.1e recent_media() accepts a base, not just a hardcoded host", (
        "base" in inspect.signature(_p.recent_media).parameters)
    yield "G2.1e prune_deleted() accepts and forwards base to recent_media", (
        "base" in inspect.signature(_m.prune_deleted).parameters
        and "base=base" in inspect.getsource(_m.prune_deleted))
    yield "G2.1e insights.py's __main__ passes its resolved base into prune_deleted", (
        "prune_deleted(token=_tok, ig_user_id=_uid, base=_base)" in (HERE / "insights.py").read_text())
    # G-2.1f: a bare total (no breakdown yet) under reach|follow_type crashed the closing print
    # with AttributeError, aborting the script before solo_fields()/followers()/report() ran —
    # dropping that day's follower-curve point even though account.json had already been saved.
    # G-2.1k Meta returns BOTH `value` and `breakdowns`; reading `value` first threw every
    # breakdown away, so reach|follow_type recorded a flat total identical to plain reach while
    # the same response carried NON_FOLLOWER 669 / FOLLOWER 40.
    # Positions, not presence: the old form is quoted in the comment that explains it, and a
    # check that raises instead of failing is a check that reports PASS by accident.
    _acct = inspect.getsource(_i.account)
    _bd = [i for i, l in enumerate(_acct.splitlines())
           if l.strip() == 'if tv.get("breakdowns"):']
    _val = [i for i, l in enumerate(_acct.splitlines())
            if l.strip() == 'elif "value" in tv:']
    yield "G2.1k a breakdown is not discarded in favour of the flat total", (
        len(_bd) == 1 and len(_val) == 1 and _bd[0] < _val[0])
    yield "G2.1f account()'s follow-type print does not assume a dict", (
        "isinstance(r, dict)" in inspect.getsource(_i.account))
    # G-2.1g: without `if: always()`, a crash anywhere in the main step (same run, same bug)
    # skips "Save the ledgers" entirely — the backfill/account writes already made to disk never
    # reach git. Same idiom daily-post.yml already uses for "Save no-repeat ledger".
    _insights_wf = (HERE / ".github/workflows/insights.yml").read_text()
    yield "G2.1g insights.yml saves the ledgers even if an earlier step crashed", (
        re.search(r"Save the ledgers\s*\n\s*if:\s*always\(\)", _insights_wf) is not None)
    # The two metrics that were hand-entered while the API had names for them. `reposts` is
    # asked ALONE now: the live endpoint rejects it (2026-11-10) though the reference lists it,
    # and in tier 0 it blanked `reels_skip_rate` on every call for a month.
    _bundled = {m for t in _p.INSIGHT_TIERS for m in t}
    yield "G2.1a reels_skip_rate and reposts are actually requested", (
        "reels_skip_rate" in _bundled
        and {"reels_skip_rate", "reposts"} <= set(_p.INSIGHT_SINGLES)
        and "reposts" not in _bundled)
    # G-2.1h The fallback must not drop the metric it is falling back for. Tier 0 carrying one
    # rejected name sent every call to the next tier, and that tier was engagement only — so
    # reels_skip_rate read 1 row out of 275 while the code "asked for it" in tier 0.
    yield "G2.1h the retention pair survives a tier-0 rejection", (
        {"reels_skip_rate", "ig_reels_avg_watch_time"} <= set(_p.INSIGHT_TIERS[1]))
    # G-2.1i Plain FIELDS read through the Facebook-login door, not api()'s. Verified live
    # 2026-11-10: copyright_check_information / has_profile_pic / is_published answer only there.
    yield "G2.1i field reads use fields_api(), not api()", (
        "def fields_api" in inspect.getsource(_i)
        and "fields_api()" in inspect.getsource(_i.solo_fields)
        and "fields_api()" in inspect.getsource(_i.account))
    # G-2.1j The scoped-insights gate must not close on `reach` alone — one answered metric
    # used to stop the post ever being asked again, which is how the retention pair stayed
    # empty even after the bundle was fixed.
    # Read the GATE LINE, not the whole function: the old expression is quoted in the comment
    # that explains why it was wrong, and a substring search over the source cannot tell the
    # explanation from the code.
    _gate = [l for l in inspect.getsource(_i.backfill).splitlines()
             if l.strip().startswith("if young and")]
    yield "G2.1j the scoped gate asks while any acted-on metric is missing", (
        len(_gate) == 1 and "issubset(got)" in _gate[0] and "not in got" not in _gate[0]
        and "def _wanted" in inspect.getsource(_i))
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
    import fetch_motion
    yield "E3 retries escalate the demand", (
        len(fetch_motion.CALMER) == 3 and "frozen photograph" in fetch_motion.CALMER[2].lower()
        and daily_src.count("fetch_motion.CALMER[attempt - 1]") == 2)
    yield "E8 shipped motion is recorded", '"motion": round(ov, 3)' in daily_src
    # A gate that silently stopped running must be a number, not a log line. Posts ship with
    # gate_ran / gate_skipped so "was this checked at all" is answerable afterwards.
    yield "H0c a gate that never ran is recorded and warned about", (
        '"gate_ran"' in daily_src and "never reached the model" in daily_src
        and "GATE_RAN" in (HERE / "fetch_image.py").read_text())
    # The clip inspection must see the RAW Veo output. If it ever ran after the verse was
    # composited it would reject every take for containing writing — verified by measurement.
    yield "A2f clip inspection runs before the verse is composited", (
        daily_src.index("clip_survives_inspection(clip") < daily_src.index("build_reel_native"))
    insights = (HERE / ".github/workflows/insights.yml").read_text()
    yield "G1 alerts only on trouble, not every post", (
        "notify.py --posted" not in daily and "python watch.py" in insights)
    # Alerts have moved twice because nobody read where they landed. The topic id must reach
    # every step that sends, or they silently go to the group's General instead.
    for _wf in ("daily-post.yml", "insights.yml", "watch.yml"):
        _src = (HERE / ".github/workflows" / _wf).read_text()
        yield (f"G1 {_wf} passes the alert topic", 
               "TELEGRAM_CHAT_ID" not in _src or "TELEGRAM_THREAD_ID" in _src)
    yield "G1 notify targets a topic when given one", (
        "message_thread_id" in (HERE / "notify.py").read_text())
    yield "G1 an alert cannot fail a post", (
        "continue-on-error: true" in insights
        and "not configured" in (HERE / "notify.py").read_text())
    watch = (HERE / "watch.py").read_text()
    yield "G1 watcher covers drop, dead and missed slots", (
        '"drop"' in watch and '"dead"' in watch and 'f"missed-' in watch
        and "COOLDOWN_DAYS" in watch)
    yield "G1 missed slots are judged per slot, within GRACE_H", (
        "SLOTS = (5, 19)" in watch and "GRACE_H = 1" in watch)
    yield "G1 missed slots ask Instagram, not the ledger", "published_times" in watch and (
        "post_instagram" in watch)
    yield "G1 the watcher runs often enough to be timely", len(
        [l for l in (HERE / ".github/workflows/watch.yml").read_text().splitlines()
         if "cron:" in l]) >= 4

    # H0-6: pip and uv picked DIFFERENT "latest" kiwipiepy on the same day (2026-10-31, 0.24.1 vs
    # 0.23.2) and disagreed on where 시편 68:19 breaks. Unpinned, "it passed in CI" and "it fails
    # locally" can both be true at once because they are not running the same tagger.
    kiwi_pins = {
        name: m.group(1) if (m := re.search(r"kiwipiepy==([0-9][0-9.]*)", text)) else None
        for name, text in (
            ("daily-post.yml", daily), ("checks.yml", checks_wf),
            ("weekly-carousel.yml", carousel_wf), ("verify.sh", verify_sh),
            # qa_gate.py's _py_prefix() copies verify.sh's uv-fallback resolution verbatim (no
            # shared module to import it from) — it carries the same pin and must drift with it.
            ("qa_gate.py", qa_src))
    }
    yield "H0-6 kiwipiepy is pinned everywhere it is installed", all(kiwi_pins.values())
    yield "H0-6 every pin is the same version", len(set(kiwi_pins.values())) == 1

    # I-1/I-2: the cron-health watchdog (RULES.md I) — a rule that only checks "does the file
    # exist" would miss the exact failure mode this was built for: someone trims WATCHLIST down,
    # or watch.py stops calling it, and every check above still passes while the watchdog goes
    # blind. So this asserts the WIRING, not just the file's existence.
    import cron_health
    watch_wf = (HERE / ".github/workflows/watch.yml").read_text()

    def _wf_text(filename):
        # A missing/renamed file must FAIL this one check, not crash the whole checks()
        # generator and hide every rule after it — the exact "loud failure, not a dead script"
        # lesson RULES.md H0-2 already states for CANNOT VERIFY.
        try:
            return (HERE / f".github/workflows/{filename}").read_text()
        except FileNotFoundError:
            return None

    # Every workflow with ITS OWN schedule: trigger must be accounted for — either watched, or
    # named in DELIBERATELY_UNWATCHED with a reason. Enumerated from disk, not retyped as a
    # second literal list here, so workflow #6 (or #8) cannot be forgotten the way weekly-carousel
    # fell through every check that existed before this file without anyone noticing for weeks.
    all_scheduled_wf = {
        p.name for p in (HERE / ".github/workflows").glob("*.yml")
        if "schedule:" in p.read_text()}
    watched = {e["file"] for e in cron_health.WATCHLIST}
    unwatched = set(cron_health.DELIBERATELY_UNWATCHED)
    yield "I-1 every scheduled workflow is either watched or deliberately excluded with a reason", (
        all_scheduled_wf <= watched | unwatched)
    yield "I-1 the deliberately-excluded list is not stale — those workflows still have a schedule", (
        unwatched <= all_scheduled_wf)
    yield "I-1 every watched workflow actually has a schedule trigger", all(
        (txt := _wf_text(e["file"])) is not None and "schedule:" in txt
        for e in cron_health.WATCHLIST)
    yield "I-1 watch.py actually calls cron_health, not just imports it", (
        "cron_health.findings()" in watch)
    yield "I-1 watch.yml grants the read-only Actions permission cron_health needs", (
        "actions: read" in watch_wf and "GITHUB_TOKEN" in watch_wf)
    # `secrets` cannot appear directly inside a step `if:` — GitHub Actions rejects it at parse
    # time ("Unrecognized named-value: 'secrets'"), which on 2026-11-09 silently invalidated the
    # ENTIRE watch.yml file (every push AND every schedule tick) until routed through `env:`
    # first. This check pins the fixed shape so a revert to the old, parse-breaking form is
    # caught here instead of by watch.py going dark.
    yield "I-2 the external heartbeat is wired, and optional by default", (
        "secrets.HEALTHCHECK_URL" in watch_wf and "env.HEALTHCHECK_URL != ''" in watch_wf)

    # J-1/J-2: "감독을 한곳에서" (RULES.md J) means control_center.py actually calls the thing it
    # claims to summarize, not just that the five files it names still happen to exist on disk —
    # the exact gap I-1's own comment warns about one section up. Checking for the MODULE name
    # (e.g. "import ig_doctor") would pass even if the one call that matters were deleted around
    # it, so this asserts the specific call each section is built on.
    cc = (HERE / "control_center.py").read_text()
    yield "J-1 control_center folds in watch.py's own findings (ops + cron, already unified)", (
        "watch.findings(" in cc)
    yield "J-1 control_center asks GitHub for the push-CI verdict checks.yml itself cannot alert on", (
        "cron_health._gh(" in cc and "checks.yml" in cc)
    # 2026-11-10: this used to check for "ig_doctor.describe(" + "ig_doctor.NEEDED" directly —
    # control_center re-reading those two on its own, with no live-probe fallback, is exactly
    # what made it report the real, working IG_INSIGHTS_TOKEN as dead on every single run
    # (debug_token cannot read an Instagram-Login token at all; ig_doctor.verdict()'s probe
    # fallback is the only thing that proves it works). The fix is calling verdict() instead of
    # describe()/NEEDED a second time — assert THAT, or a regression back to the old shape would
    # pass this check while silently reintroducing the bug it exists to catch.
    yield "J-1 control_center asks ig_doctor's shared verdict(), not a second describe()/NEEDED reading", (
        "ig_doctor.verdict(" in cc and "ig_doctor.describe(" not in cc)
    yield "J-1 control_center reports probe staleness and reference-study due-ness", (
        "ig_probe.is_stale(" in cc and "reference_study.due(" in cc)
    yield "J-2 a checks.yml failure pings the same channel watch.py alerts through", (
        "if: failure()" in checks_wf and "notify_ci_failure.py" in checks_wf)

    # K-1/K-2: "diff만 보면 안되고 전체 구조도 봐야하고, 전체 돌려도봐야하고, 결과물도
    # 뽑아봐야하고" (2026-11-10) → qa_gate.py. verify.sh never once runs daily_post.py end to
    # end, so a bug that only shows up when the real pipeline runs (carousel centering, the
    # Sunday reel eaten by the carousel) can sit behind a fully green verify.sh indefinitely.
    yield "K-1 qa_gate.py exists and imports clean", bool(qa_gate.LEDGERS)
    yield "K-1 the backup AND the restore are each verified byte-for-byte, not assumed", (
        qa_src.count("filecmp.cmp(") >= 2)
    yield "K-1 an unverified backup or restore raises instead of continuing", (
        "raise GateError" in qa_src and qa_src.count("raise GateError") >= 2)
    # Every ledger any workflow ever hands to save_ledger.sh must be in qa_gate.LEDGERS, so a new
    # ledger added to a workflow does not silently go unbacked-up the next time someone runs
    # qa_gate.py --run — the exact "forgot to register it anywhere" failure mode I-1 already
    # fixed once for WATCHLIST. verses.json is the one deliberate exception: daily_post.py only
    # reads it, never writes it (build_verses.py owns it), so a pipeline dry run cannot touch it.
    # Walked by INDENTATION, not "any following indented line" — an earlier version matched any
    # subsequently-indented line after the trigger, which (checked against this repo's own
    # workflows) swallowed an unrelated later step whole AND picked up "state.json" out of a
    # prose comment ("same shape as state.json") in reference-study.yml, because that comment's
    # own line happens to also contain the substring "save_ledger.sh" ("— see save_ledger.sh.").
    # Fix: only a line that is NOT a comment can trigger a block, and comment lines inside a
    # triggered block are excluded before token extraction either way.
    wf_ledger_tokens = set()
    for wf in (HERE / ".github/workflows").glob("*.yml"):
        lines = wf.read_text().splitlines()
        for i, line in enumerate(lines):
            if "save_ledger.sh" not in line or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" \t"))
            block = [line]
            for nxt in lines[i + 1:]:
                if not nxt.strip() or len(nxt) - len(nxt.lstrip(" \t")) < indent:
                    break
                block.append(nxt)
            text = "\n".join(l for l in block if not l.lstrip().startswith("#"))
            for tok in re.findall(r"[\w./-]+\.json\b", text):
                if "*" not in tok:
                    wf_ledger_tokens.add(tok)
    yield "K-1 qa_gate.LEDGERS covers every ledger any workflow saves (except verses.json)", (
        wf_ledger_tokens - {"verses.json"} == set(qa_gate.LEDGERS))
    yield "K-1 --run never publishes — it calls daily_post.py with --now AND --emit", (
        '"--now", "--emit"' in qa_src)
    yield "K-2 a run with no produced artifact is reported as a failure, not a pass", (
        "ok = False" in qa_src and "NO ARTIFACTS FOUND" in qa_src)
    # K-4 (2026-11-10 개정, "모든 부분들 작은거까지 전부다 예외없이 다확인"): the --run summary
    # used to print a hand-picked tuple of _meta.json keys, so a field daily_post.py started
    # writing later (or stopped writing) could drift out of what qa_gate.py showed without
    # anyone noticing — the exact "curated list quietly goes stale" shape this repo keeps
    # tripping on (WATCHLIST, LEDGERS, ACCOUNT_FIELDS). Checking for the absence of the old
    # literal tuple, not just the presence of the new loop, so a partial revert (someone adds
    # the tuple back next to the new loop "just to be safe") is still caught.
    yield "K-4 qa_gate --run prints EVERY _meta.json field, not a hand-picked subset", (
        "for k, v in meta.items():" in qa_src
        and 'for k in ("ref", "segments"' not in qa_src)


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
