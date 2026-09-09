#!/usr/bin/env python3
"""Notice when the account is going wrong, and say so once. Silent otherwise.

The daily "it posted" message was noise: two a day, every day, all fine. What is worth an
interruption is the opposite — something broke and nobody would know for days. That is exactly how
the August collapse went unseen: reach fell on 08-28 and it was spotted by eye more than a week
later, after ten duplicate posts had already been flagged.

Three things get an alert, each once per episode:
  · ENGAGEMENT DROP — recent posts are getting far fewer likes than the recent norm
  · DEAD POSTS      — several posts in a row with essentially no response
  · NO POSTS        — nothing published for longer than a day, which no failure alert would catch
                      if the workflow never ran at all (08-27: GitHub simply did not fire it)

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
RECENT_DAYS = 3          # what we are judging
BASELINE_DAYS = 18       # what we judge it against (excludes RECENT)
MIN_RECENT, MIN_BASELINE = 3, 8
DROP_RATIO = 0.5         # recent median at or below half the baseline
DEAD_LIKES, DEAD_RUN = 1, 4      # 4 posts in a row at 1 like or fewer
SILENCE_H = 30           # two posts a day means a 30-hour gap is always wrong
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


def findings():
    """[(key, message)] — key identifies the episode so it is not re-sent every day."""
    now = datetime.datetime.now(KST)
    found = []

    latest = _load(os.path.join(HERE, "metrics.json"), {})
    stamps = [(v.get("published") or "")[:19] for v in latest.values() if v.get("published")]
    if stamps:
        newest = datetime.datetime.fromisoformat(max(stamps)).replace(tzinfo=KST)
        gap = (now - newest).total_seconds() / 3600
        if gap >= SILENCE_H:
            found.append(("silence", f"⚠️ {gap:.0f}시간째 게시가 없습니다 "
                                     f"(마지막 {newest:%m/%d %H:%M})\n워크플로가 아예 안 돌았을 수 있습니다"))

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
