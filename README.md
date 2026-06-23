# 말씀 — daily scripture Instagram (auto)

A pipeline that generates and posts daily Korean 말씀 (scripture) images to Instagram,
fully hands-off. Inspired by [Alabaster Co.](https://www.alabasterco.com/) and
[@dailymayim](https://www.instagram.com/dailymayim).

## Status

- [x] **Verse → image generator** (`generate.py`) — solid muted themes + soft nature photo backgrounds.
- [x] **Photo fetcher** (`fetch_photos.py`) — pulls licensed soft-nature photos from Unsplash or Pexels.
- [x] **Instagram publishing** (`post_instagram.py`) — Meta Graph API content-publishing.
- [x] **Daily orchestrator** (`daily_post.py`) — 05:00 KST ±10 min, verse+photo→render→publish.
- [x] **Scheduler + hosting** (`.github/workflows/daily-post.yml`) — GitHub Actions, runs in cloud.
- [ ] **Your one-time setup** — Meta token + GitHub secrets (see `SETUP.md`)
- [ ] License the translation (see below)

## Quick start

```bash
# 1) get soft nature photos (free Unsplash or Pexels key — see fetch_photos.py)
#    save key to unsplash_key.txt (or pexels_key.txt)
python3 fetch_photos.py                   # default provider: unsplash
python3 fetch_photos.py --provider pexels

# 2) render verses over the photos
python3 generate.py --photos             # auto-pick a photo per verse (the main look)
python3 generate.py --all --photos       # whole verses.json, over photos

# other modes
python3 generate.py                       # today's verse, solid theme
python3 generate.py --ref "시편 23:1" --photo photos/x.jpg
python3 generate.py --theme ink           # ivory | ink | sage | clay | mist | stone
python3 generate.py --compare "시편 23:1"   # one verse across all solid themes
python3 generate.py --handle @your.handle
```

Output → `output/*.png`. Verse data → `verses.json`. Photos → `photos/`.

## Look & feel

Soft nature photography (flowers, sunsets, meadows, woods) behind elegant 명조 (serif)
type, with a gentle dreamy blur + scrim and a soft text shadow for legibility.
Photos come from **Pexels** (free commercial license, no attribution required).

## ⚠️ Copyright action item (do before scaling)

Korean Bible translations are copyrighted by **대한성서공회 (Korean Bible Society)**.
- **개역개정** (current standard) — needs a commercial license. Apply via 대한성서공회's
  저작권 사용 허락 process. This is what the audience expects; worth licensing.
- The `verses.json` shipped here is a small starter set for building/previewing the look.
  Replace with the full licensed text before going live.

## Architecture (fully hands-off)

```
daily trigger → pick verse → render PNG → upload to public URL → IG Graph API publish
```

## One-time setup you must do (for auto-publishing)

1. Convert Instagram to a **Business/Creator** account.
2. Create a **Facebook Page**, link it to the IG account.
3. Create a **Meta developer app** (developers.facebook.com) → get a long-lived **access token**
   with `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`.
4. Set up image hosting with public URLs (Cloudflare R2 / S3 / GitHub Pages).

Then the publishing script (next step) runs daily with no human in the loop.
