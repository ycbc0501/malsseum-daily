#!/usr/bin/env python3
"""Ask the token what it can do, instead of assuming. One command, one answer.

    python3 ig_doctor.py

Why this exists
---------------
For two months this project's strategy rested on the sentence "the API cannot give us reach
or shares". Nobody ever asked the token. On 2026-10-07 somebody did, and it took one call:

    GET /debug_token  →  scopes: [pages_show_list, instagram_basic,
                                  instagram_manage_comments, instagram_content_publish,
                                  pages_read_engagement, public_profile]

`instagram_manage_insights` was simply never requested. The API was never the limit. Every
`(#10) Application does not have permission` we logged was telling us this, and we read it
as "Instagram will not show us this" instead of "this token did not ask".

So this file exists to make that question cheap and repeatable. It never guesses: it reads
the granted scopes out of Meta's own debug endpoint, and it separates three things that have
been collapsed into one for two months —

    1. a permission this token does not have          → fixable, one human action
    2. a metric the API has no name for               → hand-entry forever (and that is fine)
    3. a call that failed for some other reason       → a bug

Reads `meta_secrets.txt` (gitignored) or the environment. Prints no secret.
"""

import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SECRETS = os.path.join(HERE, "meta_secrets.txt")

# What a working insights setup needs, by login type. Both doors reach the same metrics.
NEEDED = {
    "Facebook Login (현재 토큰 방식)":
        ("instagram_basic", "instagram_manage_insights", "pages_read_engagement"),
    "Instagram Login (ig_login.py)":
        ("instagram_business_basic", "instagram_business_manage_insights"),
}

# Verbatim from the Instagram media-insights reference, read 2026-10-07. These are the names
# the API answers to for a REEL. Anything here is AUTOMATABLE the moment the scope exists.
REELS_METRICS = (
    "comments", "crossposted_views", "facebook_views", "ig_reels_avg_watch_time",
    "ig_reels_video_view_total_time", "likes", "reach", "reels_skip_rate", "reposts",
    "saved", "shares", "total_interactions", "views", "total_comments", "total_likes",
    "total_views",
)

# On the 릴스 인사이트 screen but NOT in the API, at any permission level. These are the only
# numbers that stay hand-entered — and they are the ones that change slowly, so a sample
# every week or two is enough. Listed so nobody re-litigates it from memory again.
APP_ONLY = (
    "주요 조회 출처 (릴스 탭 / 탐색 탭 / 피드)",
    "또래 계정 대비 평가 (더 높음 / 더 낮음)",
    "팔로우 (이 릴에서 생긴 팔로우) — 미디어 단위로는 API에 없음",
)


def secrets():
    out = {}
    if os.path.exists(SECRETS):
        for line in open(SECRETS, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    for k in ("META_APP_ID", "META_APP_SECRET", "IG_ACCESS_TOKEN", "IG_USER_ID",
              "IG_INSIGHTS_TOKEN"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    return out


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return {"__error__": json.loads(e.read().decode())["error"]}
        except Exception:
            return {"__error__": {"code": e.code, "message": str(e)}}
    except Exception as e:
        return {"__error__": {"message": str(e)}}


def describe(token, app_id, app_secret):
    """Granted scopes for `token`, straight from Meta. Returns (info, error-or-None)."""
    app_token = f"{app_id}|{app_secret}"
    d = _get("https://graph.facebook.com/debug_token?input_token="
             + urllib.parse.quote(token) + "&access_token=" + urllib.parse.quote(app_token))
    if "__error__" in d:
        return None, d["__error__"]
    return d.get("data", {}), None


def probe(media_id, token, base, metric):
    """One metric, one call → (ok, code, message).

    NOTE, and this cost an hour to learn: when the permission is missing, Meta answers (#10)
    for EVERY metric name — including names that do not exist. `view_sources` and `navigation`
    both came back (#10) on 2026-10-07. So a (#10) sweep CANNOT be used to discover which
    metrics are real; permission is checked before the name is. Only once the scope is granted
    does a rejection mean "no such metric". The reference is the authority, not this probe."""
    r = _get(f"{base}/{media_id}/insights?metric={metric}"
             f"&access_token={urllib.parse.quote(token)}")
    if "__error__" in r:
        e = r["__error__"]
        return False, e.get("code"), str(e.get("message", ""))[:110]
    return True, None, json.dumps(r.get("data"), ensure_ascii=False)[:90]


def main():
    s = secrets()
    app_id, app_secret = s.get("META_APP_ID"), s.get("META_APP_SECRET")
    pub, ins, ig = s.get("IG_ACCESS_TOKEN"), s.get("IG_INSIGHTS_TOKEN"), s.get("IG_USER_ID")
    if not (app_id and app_secret):
        raise SystemExit("META_APP_ID / META_APP_SECRET not found "
                         "(meta_secrets.txt or environment)")

    print("=" * 78)
    print("IG DOCTOR — 이 계정이 API로 실제로 무엇을 볼 수 있는가")
    print("=" * 78)

    verdict = {}
    for label, token in (("IG_ACCESS_TOKEN (발행용)", pub), ("IG_INSIGHTS_TOKEN (읽기용)", ins)):
        print(f"\n## {label}")
        if not token:
            print("   없음" + ("   ← 이것이 있으면 인사이트가 자동화됩니다" if "INSIGHTS" in label
                               else ""))
            verdict[label] = None
            continue
        info, err = describe(token, app_id, app_secret)
        if err:
            print(f"   읽을 수 없음: ({err.get('code')}) {err.get('message')}")
            verdict[label] = None
            continue
        scopes = set(info.get("scopes") or [])
        exp = info.get("expires_at")
        print(f"   종류 {info.get('type')}   앱 {info.get('application')}   "
              f"유효 {info.get('is_valid')}   만료 {'없음' if exp in (0, None) else exp}")
        print(f"   권한 {sorted(scopes)}")
        for door, need in NEEDED.items():
            missing = [n for n in need if n not in scopes]
            mark = "✅ 충족" if not missing else f"❌ 빠짐: {missing}"
            print(f"     {door:34} {mark}")
        verdict[label] = scopes

    # Does any token we hold actually clear the insights bar?
    ok_tokens = [k for k, v in verdict.items() if v and any(
        all(n in v for n in need) for need in NEEDED.values())]

    print(f"\n{'=' * 78}\n## 판정\n{'=' * 78}")
    if ok_tokens:
        print(f"✅ 인사이트 권한이 있는 토큰: {ok_tokens}")
        print("   → insights.py 가 매일 자동으로 다음을 기록합니다:")
    else:
        print("❌ 인사이트 권한을 가진 토큰이 하나도 없습니다.")
        print("   → `(#10) Application does not have permission` 은 인스타그램이 숨기는 게")
        print("     아니라 이 토큰이 요청한 적이 없다는 뜻입니다. 사람이 한 번 고치면 끝입니다.")
        print("     절차: notes/insights-token-2026-10-07.md")
        print("   → 권한만 붙으면 다음이 전부 자동으로 들어옵니다 (지금은 손으로 넣는 것들):")
    print("     " + "  ".join(REELS_METRICS[:8]))
    print("     " + "  ".join(REELS_METRICS[8:]))
    print("\n   API 에 없어서 계속 손으로 넣어야 하는 것 — 이게 전부입니다:")
    for a in APP_ONLY:
        print(f"     · {a}")

    # A live probe, only when we have something to probe with.
    token = ins or pub
    base = ("https://graph.instagram.com/v21.0" if ins
            else "https://graph.facebook.com/v21.0")
    acct = "me" if ins else ig
    if token and acct:
        print(f"\n{'=' * 78}\n## 실제 호출 ({base})\n{'=' * 78}")
        m = _get(f"{base}/{acct}/media?fields=id,media_product_type&limit=1"
                 f"&access_token={urllib.parse.quote(token)}")
        if "__error__" in m:
            e = m["__error__"]
            print(f"   목록 조회 실패 ({e.get('code')}) {e.get('message')}")
        else:
            mid = (m.get("data") or [{}])[0].get("id")
            print(f"   대상 미디어 {mid}")
            for metric in ("reach", "views", "shares", "reels_skip_rate", "reposts",
                           "ig_reels_avg_watch_time"):
                ok, code, msg = probe(mid, token, base, metric)
                if ok:
                    print(f"     {metric:28} ✅ {msg}")
                elif code == 10:
                    print(f"     {metric:28} 권한 없음 (#10) — 지표 이름 문제가 아닙니다")
                else:
                    print(f"     {metric:28} ({code}) {msg}")
        print("\n   주의: 권한이 없을 때 Meta 는 존재하지 않는 지표 이름에도 (#10) 을 돌려줍니다.")
        print("   그러므로 위 결과로 '이 지표가 있다/없다'를 판단할 수 없습니다. 근거는 공식")
        print("   레퍼런스이고, 그 목록은 이 파일의 REELS_METRICS 에 적어 두었습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
