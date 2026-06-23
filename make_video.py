#!/usr/bin/env python3
"""
Turn a still image + audio into a Reel-ready MP4 (a still-image video with music).
Requires ffmpeg (preinstalled on GitHub Actions ubuntu runners).
"""

import subprocess


def make_video(image, audio, out, duration=14, size="1080:1920"):
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image,            # still image, looped
        "-stream_loop", "-1", "-i", audio,    # loop audio to fill the duration
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        "-vf", f"scale={size},setsar=1",
        "-af", "afade=t=in:st=0:d=1.5,afade=t=out:st=" + str(duration - 2) + ":d=2",
        "-movflags", "+faststart",
        out,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--duration", type=int, default=14)
    args = ap.parse_args()
    print(make_video(args.image, args.audio, args.out, args.duration))
