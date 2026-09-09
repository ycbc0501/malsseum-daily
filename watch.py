#!/usr/bin/env python3
"""Notice when the account is going wrong, and say so once. Silent otherwise.

The daily "it posted" message was noise: two a day, every day, all fine. What is worth an
interruption is the opposite — something broke and nobody would know for days. That is exactly how
the August collapse went unseen: reach fell on 08-28 and it was spotted by eye more than a week
later, after ten duplicate posts had already been flagged.

Three things get an alert, each once per episode:
  · ENGAGEMENT DROP — recent posts are getting far fewer likes than the recent norm
  · DEAD POSTS      — several posts in a row with essentially no response
  · MISSED SLOT     — a 05:00 or 19:00 KST post that is more than GRACE_H late. The missed-post
                      alert cannot cover this: it fires from inside a run, and on 08-27 GitHub
                      never started one, so nothing spoke at all.

Views are not available (instagram_manage_insights is still not granted), so likes are the proxy.
Run daily from the metrics workflow, after the backfill has refreshed the numbers.
"""
import datetime
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "watch.json")
KST = datetime.timezone(datetime.timedelta(hours=9))

# Likes accrue for days, so a post published hours ago is not comparable to a mature one.
MIN_AGE_H = 24
# Three days of mature posts is as few as three samples, and a median of three swings on one dud:
# on 2026-09-09 a single 0-like post put the ratio at exactly 50% and would have cried wolf. Four
# days with at least five samples costs two days of warning (first alert 08-31 rather than 08-29,
# still six days before it was noticed by eye) and buys silence on healthy noise. A detector that
# cries wolf gets ignored, which is worse than one that is a little slower.
RECENT_DAYS = 4          # what we are judging
BASELINE_DAYS = 18       # what we judge it against (excludes RECENT)
MIN_RECENT, MIN_BASELINE = 5, 8
DROP_RATIO = 0.5         # recent median at or below half the baseline
DEAD_LIKES, DEAD_RUN = 1, 4      # 4 posts in a row at 1 like or fewer
SLOTS = (5, 19)          # KST hours the account posts at
GRACE_H = 2              # late by more than this and something is wrong, not just slow
COOLDOWN_DAYS = 5        # one alert per episode, not one per day


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def posts():
    """[(published datetime KST, likes)] oldest first, mature posts only."""
    now = datetime.datetime.now(KST)
    out = []
    for v in _load(os.path.join(HERE, "metrics.json"), {}).values():
        stamp, likes = (v.get("published") or "")[:19], (v.get("insights") or {}).get("likes")
        if not stamp or likes is None:
            continue
        try:
            when = datetime.datetime.fromisoformat(stamp).replace(tzinfo=KST)
        except ValueError:
            continue
        if (now - when).total_seconds() / 3600 >= MIN_AGE_H:
            out.append((when, likes))
    return sorted(out)


def published_times():
    """When posts actually went out, asked of Instagram first.

    metrics.json is written by the posting workflow, so a run that published and then failed to
    push its ledger would leave this alert claiming the post never happened — reporting a failure
    that did not occur, which is how an alert channel loses its credibility. The account itself is
    the record (RULES.md C4); the local ledger is only the fallback when the API is unreachable."""
    try:
        import post_instagram
        out = []
        for m in post_instagram.recent_media(limit=12):
            stamp = (m.get("timestamp") or "")[:19]
            if stamp:
                out.append(datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S")
                           .replace(tzinfo=datetime.timezone.utc).astimezone(KST))
        if out:
            return out
        print("instagram returned nothing — falling back to metrics.json")
    except Exception as e:
        print(f"instagram unreachable ({e}) — falling back to metrics.json")
    out = []
    for v in _load(os.path.join(HERE, "metrics.json"), {}).values():
        stamp = (v.get("published") or "")[:19]
        if stamp:
            try:
                out.append(datetime.datetime.fromisoformat(stamp).replace(tzinfo=KST))
            except ValueError:
                pass
    return out


def findings():
    """[(key, message)] — key identifies the episode so it is not re-sent every day."""
    now = datetime.datetime.now(KST)
    found = []

    # A 30-hour silence rule was far too loose for an account that posts twice a day: the morning
    # slot could vanish and nothing would be said until the evening one did too. Each slot is
    # checked on its own, against its own deadline.
    published = published_times()
    for back in (0, 1):                      # today and yesterday, so an overnight miss is caught
        day = (now - datetime.timedelta(days=back)).date()
        for hour in SLOTS:
            slot = datetime.datetime.combine(day, datetime.time(hour), tzinfo=KST)
            deadline = slot + datetime.timedelta(hours=GRACE_H)
            if now < deadline:
                continue                     # not late yet
            # The slot owns its half of the day — the same split slot_already_filled() uses.
            lo = datetime.datetime.combine(day, datetime.time(0 if hour < 12 else 12), tzinfo=KST)
            hi = lo + datetime.timedelta(hours=12)
            if any(lo <= w < hi for w in published):
                continue
            late = (now - slot).total_seconds() / 3600
            found.append((f"missed-{day}-{hour}",
                          f"⚠️ {day:%m/%d} {hour:02d}:00 게시가 안 올라왔습니다 ({late:.0f}시간 경과)\n"
                          f"워크플로가 아예 안 돌았을 수 있습니다 — Actions 확인 필요"))

    mature = posts()
    recent = [l for w, l in mature if (now - w).days < RECENT_DAYS]
    base = [l for w, l in mature if RECENT_DAYS <= (now - w).days < BASELINE_DAYS]

    if len(recent) >= MIN_RECENT and len(base) >= MIN_BASELINE:
        r, b = statistics.median(recent), statistics.median(base)
        if b > 0 and r <= b * DROP_RATIO:
            found.append(("drop", f"⚠️ 좋아요가 떨어지고 있습니다\n"
                                  f"최근 {len(recent)}개 중앙값 {r:.0f} ← 직전 {len(base)}개 {b:.0f} "
                                  f"({r / b * 100:.0f}%)"))

    tail = [l for _, l in mature[-DEAD_RUN:]]
    if len(tail) == DEAD_RUN and all(l <= DEAD_LIKES for l in tail):
        found.append(("dead", f"⚠️ 최근 {DEAD_RUN}개 연속 반응 거의 없음 (좋아요 {tail})\n"
                              f"도달 제한을 의심해 보세요 — 설정 → 계정 상태 → 도달"))
    return found


def main():
    state = _load(STATE, {})
    today = datetime.datetime.now(KST).date()
    sent = []
    for key, message in findings():
        last = state.get(key)
        if last:
            try:
                if (today - datetime.date.fromisoformat(last)).days < COOLDOWN_DAYS:
                    print(f"{key}: still within cooldown, not re-sending")
                    continue
            except ValueError:
                pass
        import notify
        if notify.send(message):
            state[key] = today.isoformat()
            sent.append(key)
        print(f"{key}: {message.splitlines()[0]}")
    # Clear an episode once it stops firing, so the next one alerts immediately.
    live = {k for k, _ in findings()}
    for key in list(state):
        if key not in live:
            del state[key]
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    if not sent:
        print("watch: nothing worth interrupting for")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
