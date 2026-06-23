# Setup — going fully hands-off

One-time setup so the daily 5 AM KST post runs by itself. ~30–45 min.

There are two parts: **(A) Instagram/Meta** (to get a token) and **(B) GitHub** (to run it).

---

## A. Instagram + Meta Graph API

The official, ToS-compliant way to auto-publish. You need an Instagram **Business** (or
Creator) account linked to a Facebook Page, then a Meta app + access token.

1. **Make the IG account a Business/Creator account**
   Instagram app → Settings → Account type → switch to *Business* (or *Creator*).

2. **Create a Facebook Page and link it**
   facebook.com → create a Page (free). Then in Instagram: Settings → *Linked accounts* /
   *Page* → connect the Page. (Meta's publishing API requires this link.)

3. **Create a Meta app**
   https://developers.facebook.com → My Apps → *Create App* → type **Business**.
   Add the **Instagram Graph API** product.

4. **Get your IDs and token** (easiest via the Graph API Explorer)
   - In the app dashboard open *Tools → Graph API Explorer*.
   - Grant permissions: `instagram_basic`, `instagram_content_publish`,
     `pages_show_list`, `pages_read_engagement`, `business_management`.
   - Get your **Instagram Business account id** (`IG_USER_ID`):
     `GET /me/accounts` → find your Page → `GET /{page-id}?fields=instagram_business_account`.
   - Generate an **access token**.

5. **Make the token long-lived / non-expiring (important for hands-off!)**
   A normal token expires in ~1–2 hours; a "long-lived" one lasts ~60 days. For a feed
   that should never break, use a **System User token** (can be set to never expire):
   business.facebook.com → *Business settings → Users → System users* → add a system user →
   assign the app + Page → *Generate token* with the permissions above → set no expiry.
   Use that as `IG_ACCESS_TOKEN`.

> Keep `IG_USER_ID` and `IG_ACCESS_TOKEN` — you'll paste them into GitHub secrets below.

---

## B. GitHub (the runner + image host)

1. **Create a repo** (private is fine) and push this folder to it:
   ```bash
   cd /Users/memyselfi/Documents/bible
   git init && git add . && git commit -m "말씀 daily poster"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
   (`pexels_key.txt` is gitignored and will NOT be pushed — good.)

2. **Add secrets**: repo → *Settings → Secrets and variables → Actions → New repository secret*
   - `IG_USER_ID` = your Instagram Business account id
   - `IG_ACCESS_TOKEN` = your long-lived/system-user token

3. **Test it**: repo → *Actions* tab → "Daily 말씀 post" → *Run workflow* (manual trigger).
   - It will wait until 05:00 KST ±10 min, render, commit the image, and publish.
   - For an *instant* test without waiting, temporarily change the workflow step to
     `python daily_post.py --emit --now`.

4. **Done.** From then on it posts every morning at ~5 AM KST automatically.

---

## Notes / gotchas

- **Photos**: a pool of ~40 soft-nature photos lives in `photos/` (committed). Refresh
  anytime with `python fetch_photos.py` and push. Or switch to fetching fresh daily later.
- **Token refresh**: if you used a 60-day token instead of a system-user token, it will
  expire — set a calendar reminder to regenerate, or switch to a system-user token.
- **Translation license**: `verses.json` is a small starter set. License 개역개정 from
  대한성서공회 before scaling the content commercially (see README).
- **Rate/quality**: Instagram allows ~25 API posts/24h — far more than 1/day. Fine.
