#!/usr/bin/env python3
"""
Build a Reel MP4 from a background video clip + a transparent text overlay + music.
Requires ffmpeg (preinstalled on GitHub Actions ubuntu runners).
"""

import subprocess

W, H = 1080, 1920
_COVER = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"


def extract_frame(video, out_png, at=0.8):
    """Grab one representative frame (cropped to 9:16) for color/placement analysis."""
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(at), "-i", video,
        "-vf", _COVER, "-frames:v", "1", out_png,
    ], check=True, capture_output=True)
    return out_png


def make_boomerang(clip, out):
    """Forward + reverse → a seamless loop (~2× the clip length, no jump cut)."""
    subprocess.run([
        "ffmpeg", "-y", "-i", clip,
        "-filter_complex", "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]",
        "-map", "[v]", "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-preset", "ultrafast", "-crf", "28",
        out,
    ], check=True, capture_output=True)
    return out


def build_reel(video, overlay_png, audio, out, duration=60):
    """Background video (boomerang, looped/cropped to 9:16) + text overlay + music → MP4."""
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", video,        # 0: bg video (loop to fill duration)
        "-i", overlay_png,                         # 1: text overlay (static)
        "-stream_loop", "-1", "-i", audio,         # 2: music (loop to fill)
        "-filter_complex",
        f"[0:v]{_COVER}[bg];[bg][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-preset", "veryfast", "-crf", "26",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        "-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration - 2}:d=2",
        "-movflags", "+faststart",
        out,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


# still image + music → MP4 (the still-card Reel). size defaults to the 4:5 card.
def make_video(image, audio, out, duration=14, size=(1080, 1350)):
    w, h = size
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", image,
        "-stream_loop", "-1", "-i", audio,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        "-vf", f"scale={w}:{h},setsar=1",
        "-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration - 2}:d=2",
        "-movflags", "+faststart",
        out,
    ], check=True, capture_output=True)
    return out
