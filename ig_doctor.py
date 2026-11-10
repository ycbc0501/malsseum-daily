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
              "IG_INSIGHTS_TOKEN", "IG_APP_ID", "IG_APP_SECRET"):
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


DISPLAY = {"IG_ACCESS_TOKEN": "IG_ACCESS_TOKEN (발행용)", "IG_INSIGHTS_TOKEN": "IG_INSIGHTS_TOKEN (읽기용)"}
EXPECT_OK = ("reach", "views", "shares", "reels_skip_rate", "ig_reels_avg_watch_time")


def verdict(s=None):
    """The one place that decides whether a token clears the insights bar — debug_token where it
    can answer, a live metric probe where it structurally cannot (Instagram-Login tokens; see the
    comment this used to carry inline in main()). Returns plain env-var-name keys
    ("IG_ACCESS_TOKEN"/"IG_INSIGHTS_TOKEN"), not the Korean display labels, so a caller like
    control_center.py doesn't have to know main()'s print formatting to ask "is this token ok".

    2026-11-10: before this existed, control_center.token_section() re-read describe()/NEEDED on
    its own and had no fallback probe — so it reported the IG_INSIGHTS_TOKEN as dead every single
    run, forever, even though main()'s own fallback probe (right below) already proves it works.
    Two readings of the same question had drifted; this is the one implementation both now share.
    """
    s = s or secrets()
    app_id, app_secret = s.get("META_APP_ID"), s.get("META_APP_SECRET")
    ig_app_id, ig_app_secret = s.get("IG_APP_ID"), s.get("IG_APP_SECRET")
    pub, ins, ig = s.get("IG_ACCESS_TOKEN"), s.get("IG_INSIGHTS_TOKEN"), s.get("IG_USER_ID")
    creds = {
        "IG_ACCESS_TOKEN": (app_id, app_secret),
        "IG_INSIGHTS_TOKEN": (ig_app_id or app_id, ig_app_secret or app_secret),
    }
    info_by_key, errors, debug_token_unreachable = {}, {}, set()
    for key, token in (("IG_ACCESS_TOKEN", pub), ("IG_INSIGHTS_TOKEN", ins)):
        if not token:
            continue
        a_id, a_secret = creds[key]
        info, err = describe(token, a_id, a_secret)
        if err:
            errors[key] = err
            debug_token_unreachable.add(key)
        else:
            info_by_key[key] = info

    ok_tokens = [key for key, info in info_by_key.items() if any(
        all(n in (info.get("scopes") or []) for n in need) for need in NEEDED.values())]

    # Only probe when debug_token actually failed to answer for the token we'd use to read —
    # that is the one case where the probe result changes the verdict, and the only case where
    # this repo has ever needed it. A Facebook-Login token that debug_token can already read
    # never reaches this branch, so the common case stays as cheap as it always was.
    probe_key = "IG_INSIGHTS_TOKEN" if ins else "IG_ACCESS_TOKEN"
    probe_lines = []
    if probe_key in debug_token_unreachable:
        token = ins or pub
        base = "https://graph.instagram.com/v21.0" if ins else "https://graph.facebook.com/v21.0"
        acct = "me" if ins else ig
        if token and acct:
            m = _get(f"{base}/{acct}/media?fields=id,media_product_type&limit=1"
                     f"&access_token={urllib.parse.quote(token)}")
            if "__error__" in m:
                e = m["__error__"]
                probe_lines.append(f"   목록 조회 실패 ({e.get('code')}) {e.get('message')}")
            else:
                mid = (m.get("data") or [{}])[0].get("id")
                probe_lines.append(f"   대상 미디어 {mid}")
                succeeded = set()
                for metric in EXPECT_OK + ("reposts",):
                    ok, code, msg = probe(mid, token, base, metric)
                    if ok:
                        probe_lines.append(f"     {metric:28} ✅ {msg}")
                        succeeded.add(metric)
                    elif code == 10:
                        probe_lines.append(f"     {metric:28} 권한 없음 (#10) — 지표 이름 문제가 아닙니다")
                    else:
                        probe_lines.append(f"     {metric:28} ({code}) {msg}")
                if all(m in succeeded for m in EXPECT_OK) and probe_key not in ok_tokens:
                    ok_tokens.append(probe_key)

    return {
        "ok_tokens": ok_tokens,
        "debug_token_unreachable": debug_token_unreachable,
        "info_by_key": info_by_key,
        "errors": errors,
        "probe_lines": probe_lines,
        "probe_key": probe_key,
    }


def main():
    s = secrets()
    app_id, app_secret = s.get("META_APP_ID"), s.get("META_APP_SECRET")
    if not (app_id and app_secret):
        raise SystemExit("META_APP_ID / META_APP_SECRET not found "
                         "(meta_secrets.txt or environment)")

    print("=" * 78)
    print("IG DOCTOR — 이 계정이 API로 실제로 무엇을 볼 수 있는가")
    print("=" * 78)

    # IG_ACCESS_TOKEN comes from Facebook Login (minted under META_APP_ID) and IG_INSIGHTS_TOKEN
    # comes from Instagram Login (minted under IG_APP_ID, ig_login.py) — two different apps.
    # debug_token's app_token must belong to the SAME app that issued the input_token, or Meta
    # answers with an unrelated-looking error (seen here as "(#2) Service temporarily
    # unavailable", which is not a permission problem at all). Debugging the wrong token with
    # the wrong app's credentials is how this file nearly reported a working token as dead.
    #
    # For Instagram-Login tokens (ig_login.py) debug_token is not just wrong-app, it refuses the
    # token type outright — (#2) "Service temporarily unavailable" or (#190)/(#10) depending on
    # which app's credentials are used, tried on 2026-11-10 with every combination. That is a
    # product limitation of this token type, not a missing scope: the exchange response from
    # ig_login.py already printed the granted scopes once, at mint time, and that is the only
    # place Meta will ever say them for this door. verdict() below judges that case by whether
    # its actual metric calls succeed, not by whether debug_token can see it.
    v = verdict(s)

    for key in ("IG_ACCESS_TOKEN", "IG_INSIGHTS_TOKEN"):
        print(f"\n## {DISPLAY[key]}")
        token = s.get(key)
        if not token:
            print("   없음" + ("   ← 이것이 있으면 인사이트가 자동화됩니다" if key == "IG_INSIGHTS_TOKEN"
                               else ""))
            continue
        if key in v["errors"]:
            err = v["errors"][key]
            print(f"   읽을 수 없음: ({err.get('code')}) {err.get('message')}")
            continue
        info = v["info_by_key"][key]
        scopes = set(info.get("scopes") or [])
        exp = info.get("expires_at")
        print(f"   종류 {info.get('type')}   앱 {info.get('application')}   "
              f"유효 {info.get('is_valid')}   만료 {'없음' if exp in (0, None) else exp}")
        print(f"   권한 {sorted(scopes)}")
        for door, need in NEEDED.items():
            missing = [n for n in need if n not in scopes]
            mark = "✅ 충족" if not missing else f"❌ 빠짐: {missing}"
            print(f"     {door:34} {mark}")

    ok_tokens = [DISPLAY[k] for k in v["ok_tokens"]]
    print(f"\n{'=' * 78}\n## 판정\n{'=' * 78}")
    if ok_tokens:
        print(f"✅ 인사이트 권한이 있는 토큰: {ok_tokens}")
        if any(k in v["debug_token_unreachable"] for k in v["ok_tokens"]):
            print("   (debug_token 은 이 토큰 종류를 볼 수 없어서 못 썼습니다 — 판정은 아래")
            print("    '실제 호출'이 전부 성공한 것으로 내렸습니다. 추측이 아니라 실측입니다.)")
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

    if v["probe_lines"]:
        ins = s.get("IG_INSIGHTS_TOKEN")
        base = "https://graph.instagram.com/v21.0" if ins else "https://graph.facebook.com/v21.0"
        print(f"\n{'=' * 78}\n## 실제 호출 ({base})\n{'=' * 78}")
        for line in v["probe_lines"]:
            print(line)
        print("\n   주의: 권한이 없을 때 Meta 는 존재하지 않는 지표 이름에도 (#10) 을 돌려줍니다.")
        print("   그러므로 위 결과로 '이 지표가 있다/없다'를 판단할 수 없습니다. 근거는 공식")
        print("   레퍼런스이고, 그 목록은 이 파일의 REELS_METRICS 에 적어 두었습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
