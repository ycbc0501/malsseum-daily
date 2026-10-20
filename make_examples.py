#!/usr/bin/env python3
"""게시물 샘플을 뽑는다 — 실제 게시 경로 그대로, 인스타그램에는 올리지 않는다.

    python3 make_examples.py                          무작위 5개
    python3 make_examples.py --refs "시편 23:1" "잠언 3:6"
    python3 make_examples.py --count 10 --out ~/Desktop/샘플

왜 있나: 조판이나 줄바꿈을 고칠 때마다 "보여 달라"가 따라오고, 그때마다 임시 스크립트를
다시 짜게 된다. 2026-10 세션에서만 다섯 번 그랬다. 샘플은 **실제 렌더 경로**
(`generate.render_text_overlay`)를 타야 의미가 있으므로 여기서 한 번만 짜 둔다.

배경은 `--bg`로 준 폴더에서 재사용하고, 모자라면 `fetch_higgsfield`로 만든다
(이미지 1장 ≈ ₩250, 영상은 만들지 않는다 — 조판을 보는 데는 정지 화면이면 된다).
"""
import argparse
import contextlib
import io
import json
import os
import sys

from PIL import Image, ImageDraw

import generate

HERE = os.path.dirname(os.path.abspath(__file__))


def _verses():
    with open(os.path.join(HERE, "verses.json")) as f:
        return json.load(f)["verses"]


def _lines_of(verse):
    """그 구절이 몇 줄로 앉는지 — 실제 분줄기에 물어본다."""
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    with contextlib.redirect_stdout(io.StringIO()):
        return generate.fit_verse(probe, verse["text"],
                                  generate.verse_col_w(generate.REEL), 44)[1]


def render_one(verse, bg_path, dest):
    """배경 1장 + 말씀 1개 → 게시물 1장. 오버레이는 실제 경로를 그대로 쓴다."""
    bg = generate.cover_crop(Image.open(bg_path).convert("RGB"), *generate.REEL)
    tmp = dest + ".overlay.png"
    with contextlib.redirect_stdout(io.StringIO()):
        generate.render_text_overlay(verse, tmp, canvas=generate.REEL,
                                     placement=("center", "top"), bg=bg)
    overlay = Image.open(tmp).convert("RGBA")
    Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB").save(dest, quality=94)
    os.remove(tmp)
    return dest


def _backgrounds(folder, need):
    """폴더의 배경을 쓰고, 모자란 만큼만 새로 만든다."""
    os.makedirs(folder, exist_ok=True)
    have = sorted(f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg")))
    paths = [os.path.join(folder, f) for f in have][:need]
    if len(paths) >= need:
        return paths
    import fetch_higgsfield
    state_i = 0
    with contextlib.suppress(Exception):
        with open(os.path.join(HERE, "state.json")) as f:
            state_i = json.load(f).get("scene_i", 0)
    for n in range(len(paths), need):
        out = os.path.join(folder, f"bg{n + 1:02d}.png")
        idx = (state_i + n * 13) % len(fetch_higgsfield.SCENES)
        with contextlib.redirect_stdout(io.StringIO()):
            fetch_higgsfield.generate_background(out, idx, ("center", "top"),
                                                 aspect="9:16", var_t=n * 5)
        print(f"  배경 {n + 1}/{need}  {fetch_higgsfield.SCENE_CATS[idx]}", flush=True)
        paths.append(out)
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refs", nargs="*", help="구절 참조. 없으면 풀에서 고르게 뽑는다")
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--out", default=os.path.expanduser("~/Desktop/말씀샘플"))
    ap.add_argument("--bg", default=os.path.join(HERE, ".samples", "bg"),
                    help="배경 캐시 폴더 — 있으면 다시 쓰고 모자라면 만든다")
    args = ap.parse_args()

    pool = _verses()
    if args.refs:
        by_ref = {v["ref"]: v for v in pool}
        missing = [r for r in args.refs if r not in by_ref]
        if missing:
            sys.exit(f"구절 풀에 없습니다: {missing}")
        picks = [by_ref[r] for r in args.refs]
    else:
        # 고르게 건너뛰며 — 고르면 시험이 되지 않는다
        step = max(1, len(pool) // args.count)
        picks = [pool[i * step] for i in range(args.count)]

    os.makedirs(args.out, exist_ok=True)
    bgs = _backgrounds(args.bg, len(picks))
    for i, (verse, bg) in enumerate(zip(picks, bgs), 1):
        name = verse["ref"].replace(" ", "").replace(":", "-")
        dest = os.path.join(args.out, f"{i:02d}_{name}.jpg")
        render_one(verse, bg, dest)
        print(f"{i:02d} {verse['ref']:16} {len(_lines_of(verse))}줄  {dest}")
    print(f"\n{len(picks)}장 → {args.out}")


if __name__ == "__main__":
    main()
