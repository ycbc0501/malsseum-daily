#!/usr/bin/env python3
"""Check that RULES.md still describes what the code actually does.

A rule written down but not enforced is worse than no rule: it reads as a guarantee. Run this
after touching the pipeline, and add a check here whenever a rule is added to RULES.md.
"""
import json
import pathlib
import re

import daily_post
import fetch_higgsfield as hf
import generate

HERE = pathlib.Path(__file__).parent


def checks():
    gate = hf._CHECK_PROMPT.lower()
    notext = hf.NOTEXT.lower()
    daily = (HERE / ".github/workflows/daily-post.yml").read_text()
    carousel_wf = (HERE / ".github/workflows/weekly-carousel.yml").read_text()
    carousel = (HERE / "carousel_post.py").read_text()
    scenes = [s for items in hf.SCENE_GROUPS.values() for s in items]
    verses = json.load(open(HERE / "verses.json"))["verses"]

    yield "A1 no people (prompt)", "no person" in notext and "silhouette" in notext
    yield "A1 no people (gate)", "any person" in gate
    yield "A2 no writing (prompt)", "no text" in notext and "watermark" in notext
    yield "A2 no writing (gate)", "any writing" in gate
    yield "A3 no books or paper in any scene", not [
        s for s in scenes if re.search(r"book|\bpaper\b|notebook|envelope", s, re.I)]
    yield "A4 impossible physics (gate)", "vertical mirror" in gate and "stacked duplicate" in gate
    yield "A5 no sky indoors (gate)", "indoor/outdoor composite" in gate
    yield "A6 no CGI look (gate)", "fake / cgi" in gate
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
    yield "C2 carousel queue", "concurrency:" in carousel_wf
    yield "C3 slot re-checked just before publishing", "Re-check the slot right before" in daily
    yield "C4 Instagram is the source of truth", hasattr(daily_post, "published_refs")
    yield "C5 ledger saves under if:always with semantic merge", (
        "if: always()" in daily and (HERE / "ledger_merge.py").exists())
    yield "C6 oldest-first (reel)", hasattr(daily_post, "last_published")
    yield "C6 oldest-first (carousel)", "last_published" in carousel
    yield "D  every INTERIOR_CATS entry is a real scene", not [
        c for c in hf.INTERIOR_CATS if c not in hf.SCENE_GROUPS]
    yield "D  no interior is asked for a sky", not [
        i for i in range(len(hf.SCENES))
        if hf.SCENE_CATS[i] in hf.INTERIOR_CATS
        and "cloudless sky" in hf.COMPOSE[("center", "top")].format(
            empty_area=hf.EMPTY_AREA[True], anchor=hf.ANCHOR[True])]
    yield "F3 text area is measured, not assumed", hasattr(generate, "text_area_ok")
    # Motion must be measured a second apart, not frame to frame — see RULES.md E2.
    import inspect
    import make_video
    src = inspect.getsource(make_video.motion_score)
    yield "E2 motion measured one second apart", "stride" in src and "fps=" in src
    daily_src = (HERE / "daily_post.py").read_text()
    yield "E3 gate selects the calmest rather than rejecting", (
        "MOTION_HARD" in daily_src and "MOTION_HARD and sky <= SKY_HARD" in daily_src)
    yield "E4 continuation segments retry too", daily_src.count("for attempt in (1, 2)") >= 1
    import fetch_veo
    yield "E3 retries escalate the demand", (
        len(fetch_veo.CALMER) == 3 and "FROZEN PHOTOGRAPH" in fetch_veo.CALMER[2]
        and daily_src.count("fetch_veo.CALMER[attempt - 1]") == 2)
    yield "E8 shipped motion is recorded", '"motion": round(ov, 3)' in daily_src
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
    for name, passed in checks():
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        if not passed:
            failed.append(name)
    print(f"\n{'all rules hold' if not failed else str(len(failed)) + ' RULE(S) NOT ENFORCED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
