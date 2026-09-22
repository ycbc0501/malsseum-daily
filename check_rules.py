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
    # A5b — the seam gate must be MEASURED and must run even when the model said yes, because on
    # 2026-09-14 the model said yes to a stacked composite and it shipped.
    yield "A5b stacked composites are measured, not asked about", hasattr(hf, "has_seam")
    yield "A5b the seam gate runs even when the model approves", (
        "if ok and has_seam(dest)" in (HERE / "fetch_higgsfield.py").read_text())
    yield "A5b both thresholds must trip", (
        hf.SEAM_JUMP >= 5.0 and hf.SEAM_RATIO >= 20.0)
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
    yield "B5 a failed reflection still produces a caption", (
        not reflection.enabled()
        and daily_post.build_caption(verse, "") == f"{verse['text']}\n[{verse['ref']}]")
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
    yield "E2b motion is recorded, not a reason to regenerate", (
        "RECORDED, never a reason to regenerate" in daily_src)
    yield "E3 gate selects the calmest rather than rejecting", (
        "MOTION_HARD" in daily_src and "MOTION_HARD and sky <= SKY_HARD" in daily_src)
    # Continuations are inspected and retry only on a real defect — they used to take two takes,
    # choose on the motion number, and inspect neither.
    yield "E4 continuations are inspected", "clip_survives_inspection(nxt" in daily_src
    yield "E4 a retry needs a real defect, not a motion number", (
        "if s_ov <= MOTION_MAX" not in daily_src and "VEO_TRIES" in daily_src)
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
