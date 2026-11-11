#!/usr/bin/env python3
"""RULES.md D-6 — reference photographs are persisted (reference_study.save_style_ref) and then
actually attached to the Gemini call (fetch_image._pick_style_refs / _image_request_body), instead
of being classified once and thrown away. No test here touches the network or the real
notes/reference-study/style_refs/ directory — every call below passes an explicit tmp path.
"""
import base64
import json
import os
import shutil
import sys
import tempfile

import content_law
import fetch_image as hf
import reference_study as rs

FAIL = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
    if not cond:
        FAIL.append(name)


real_dir_snapshot = sorted(os.listdir(hf.STYLE_REF_DIR)) if os.path.isdir(hf.STYLE_REF_DIR) else None

tmp = tempfile.mkdtemp()
try:
    # -----------------------------------------------------------------------------------------
    # reference_study.save_style_ref — persistence + bounded rotation.
    # -----------------------------------------------------------------------------------------
    src = os.path.join(tmp, "src.jpg")
    with open(src, "wb") as f:
        f.write(b"\xff\xd8not a real jpeg but bytes are bytes for this test")

    pool = os.path.join(tmp, "pool")
    dest = rs.save_style_ref(src, ["dailymayim"], dirpath=pool)
    check("save_style_ref returns the path it actually wrote", dest and os.path.exists(dest))
    check("the saved file is a byte-for-byte copy of the source",
          open(dest, "rb").read() == open(src, "rb").read())
    check("the saved filename carries the account handle", "dailymayim" in os.path.basename(dest))

    for _ in range(rs.STYLE_REF_CAP + 5):
        rs.save_style_ref(src, ["dailymayim"], dirpath=pool)
    pool_files = sorted(os.listdir(pool))
    check("the pool is capped at STYLE_REF_CAP, not left to grow without bound",
          len(pool_files) == rs.STYLE_REF_CAP)
    # Reverse-test: prove the cap is actually being ENFORCED, not just coincidentally equal to
    # the count above — a pool with the eviction loop deleted would hold every file ever written.
    pool2 = os.path.join(tmp, "pool_no_cap_check")
    n_written = rs.STYLE_REF_CAP + 5
    for _ in range(n_written):
        rs.save_style_ref(src, ["dailymayim"], dirpath=pool2)
    check("reverse-test would catch a missing eviction loop: writing CAP+5 files left exactly "
          "CAP, not CAP+5", len(os.listdir(pool2)) == rs.STYLE_REF_CAP != n_written)

    # Reverse-test for the code-review fix (2026-11-11): eviction must track real file age, not
    # the filename string — a multi-account pool where names sort "backwards" relative to save
    # order would evict the WRONG (newest) file if eviction ever regressed to a filename sort.
    pool3 = os.path.join(tmp, "pool_multi_account")
    old_file = rs.save_style_ref(src, ["zzz_acct"], dirpath=pool3)
    import time as _time
    _time.sleep(0.01)
    new_file = rs.save_style_ref(src, ["aaa_acct"], dirpath=pool3)
    check("setup: the second save really is newer on disk",
          os.path.getmtime(new_file) > os.path.getmtime(old_file))
    for _ in range(rs.STYLE_REF_CAP - 1):
        rs.save_style_ref(src, ["mmm_acct"], dirpath=pool3)
    check("reverse-test would catch a filename-sort regression: the OLDEST file (zzz_acct, "
          "which sorts AFTER aaa_acct by name) is evicted, not the newest",
          not os.path.exists(old_file) and os.path.exists(new_file))

    check("save_style_ref never touched the REAL style_refs directory",
          (sorted(os.listdir(hf.STYLE_REF_DIR)) if os.path.isdir(hf.STYLE_REF_DIR) else None)
          == real_dir_snapshot)

    # A failing copy (bad src path) must not raise — a save that cannot run must not be able to
    # stop the classification/report it is called alongside (rule 0-3's shape).
    bad = rs.save_style_ref(os.path.join(tmp, "does-not-exist.jpg"), ["dailymayim"],
                            dirpath=os.path.join(tmp, "pool3"))
    check("a failed save returns None instead of raising", bad is None)

    # -----------------------------------------------------------------------------------------
    # fetch_image._style_refs / _pick_style_refs — reading the pool back.
    # -----------------------------------------------------------------------------------------
    orig_dir = hf.STYLE_REF_DIR
    empty_dir = os.path.join(tmp, "empty")
    try:
        hf.STYLE_REF_DIR = os.path.join(tmp, "does-not-exist-at-all")
        check("_style_refs() on a missing directory returns [], not an exception", hf._style_refs() == [])
        check("_pick_style_refs() on a missing directory returns [], not an exception",
              hf._pick_style_refs() == [])

        os.makedirs(empty_dir)
        hf.STYLE_REF_DIR = empty_dir
        check("_style_refs() on an EMPTY real directory also returns []", hf._style_refs() == [])

        hf.STYLE_REF_DIR = pool
        refs = hf._style_refs()
        check("_style_refs() sees every saved tile", len(refs) == rs.STYLE_REF_CAP)
        check("_style_refs() only lists image files", all(
            p.lower().endswith((".jpg", ".jpeg", ".png")) for p in refs))
        picked = hf._pick_style_refs(n=2)
        check("_pick_style_refs(n=2) returns at most 2", len(picked) <= 2)
        check("_pick_style_refs() never returns more than the pool actually has", (
            len(hf._pick_style_refs(n=999)) == len(refs)))
    finally:
        hf.STYLE_REF_DIR = orig_dir

    # -----------------------------------------------------------------------------------------
    # content_law.for_image — the style_ref note is conditional, and OFF by default (no
    # regression for a repo with nothing in STYLE_REF_DIR yet).
    # -----------------------------------------------------------------------------------------
    plain = content_law.for_image("a quiet field", "soft light", "COMPOSITION: wide")
    with_note = content_law.for_image("a quiet field", "soft light", "COMPOSITION: wide", style_ref=True)
    check("style_ref defaults to False — identical prompt to before this feature existed",
          plain == content_law.for_image("a quiet field", "soft light", "COMPOSITION: wide", style_ref=False))
    check("style_ref=True adds the look-and-feel note", content_law.STYLE_REF_NOTE in with_note)
    check("style_ref=False (default) never adds it", content_law.STYLE_REF_NOTE not in plain)
    check("the note tells the model the SUBJECT is still the words, not the photos",
          "words below" in content_law.STYLE_REF_NOTE.lower())
    check("the note tells the model NOT to copy composition/subject",
          "do not copy" in content_law.STYLE_REF_NOTE.lower())
    check("every absolute law still appears whether or not a style ref is attached",
          all(m in with_note for m in ("NO WRITING", "NO PEOPLE", "REAL THINGS ONLY", "FILMED, NOT MADE")))

    # -----------------------------------------------------------------------------------------
    # fetch_image._image_request_body — pure request assembly, no network.
    # -----------------------------------------------------------------------------------------
    body_no_refs = hf._image_request_body("a prompt", "3:4", None)
    parts0 = body_no_refs["contents"][0]["parts"]
    check("with no style refs, the body has exactly one part: the text",
          len(parts0) == 1 and parts0[0] == {"text": "a prompt"})

    jpg = os.path.join(tmp, "ref1.jpg")
    with open(jpg, "wb") as f:
        f.write(b"fake-jpeg-bytes")
    png = os.path.join(tmp, "ref2.png")
    with open(png, "wb") as f:
        f.write(b"fake-png-bytes")

    body = hf._image_request_body("a prompt", "3:4", [jpg, png])
    parts = body["contents"][0]["parts"]
    check("images come BEFORE the text part, same convention as check_composition",
          len(parts) == 3 and parts[-1] == {"text": "a prompt"})
    check("a .jpg reference is tagged image/jpeg", parts[0]["inlineData"]["mimeType"] == "image/jpeg")
    check("a .png reference is tagged image/png", parts[1]["inlineData"]["mimeType"] == "image/png")
    check("the inline data really is this file's own bytes, base64-encoded",
          base64.b64decode(parts[0]["inlineData"]["data"]) == b"fake-jpeg-bytes")
    check("aspect ratio still reaches generationConfig the same way as before",
          body["generationConfig"]["imageConfig"]["aspectRatio"] == "3:4")

    # A reference that vanished between _pick_style_refs() and the actual call must not take the
    # whole render down with it (rule 0-3's shape) — only the text part should survive.
    gone = os.path.join(tmp, "vanished.jpg")
    body_missing = hf._image_request_body("a prompt", "3:4", [gone])
    check("a missing reference file is skipped, not raised",
          body_missing["contents"][0]["parts"] == [{"text": "a prompt"}])

    # -----------------------------------------------------------------------------------------
    # generate_background actually wires style refs through — without hitting the network, by
    # checking the prompt handed to a stubbed _gemini() rather than calling Gemini for real.
    # -----------------------------------------------------------------------------------------
    orig_gemini = hf._gemini
    orig_dir = hf.STYLE_REF_DIR
    captured = {}
    try:
        hf.STYLE_REF_DIR = pool   # has STYLE_REF_CAP real tiles from above

        def _fake_gemini(prompt, dest, aspect="3:4", style_refs=None):
            captured["prompt"] = prompt
            captured["style_refs"] = style_refs
            with open(dest, "wb") as f:
                f.write(b"fake-background")
            return dest

        hf._gemini = _fake_gemini
        out = os.path.join(tmp, "bg.png")
        hf.generate_background(out, index=0)
        check("generate_background actually passed non-empty style_refs through to _gemini",
              bool(captured.get("style_refs")))
        check("generate_background's prompt carries the look-and-feel note when refs are attached",
              content_law.STYLE_REF_NOTE in captured["prompt"])

        hf.STYLE_REF_DIR = empty_dir
        captured.clear()
        hf.generate_background(out, index=0)
        check("with an empty pool, style_refs is empty and the note is absent — no regression",
              captured.get("style_refs") == []
              and content_law.STYLE_REF_NOTE not in captured["prompt"])
    finally:
        hf._gemini = orig_gemini
        hf.STYLE_REF_DIR = orig_dir
finally:
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    print(f"\n{len(FAIL)} failing" if FAIL else "\nall ok")
    sys.exit(1 if FAIL else 0)
