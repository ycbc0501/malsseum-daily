#!/usr/bin/env python3
"""
Build a Reel MP4 from a background video clip + a transparent text overlay + music.
Requires ffmpeg (preinstalled on GitHub Actions ubuntu runners).
"""

import shutil
import subprocess

W, H = 1080, 1920
_COVER = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"


def _ffmpeg():
    """Resolve an ffmpeg binary: system PATH (GitHub Actions) → bundled imageio-ffmpeg (local)."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FFMPEG = _ffmpeg()


def build_reel_still(bg_png, overlay_png, audio, out, duration=20):
    """Still background → Reel, done in the RIGHT order: zoom the BACKGROUND first
    (gentle Ken Burns), THEN composite the verse text statically on top. The text is
    added AFTER the zoom, so it never scales or shakes with the motion, and it never
    passes through the zoom's resampling — it stays pixel-crisp at native resolution.

    (Replaces the old make_reel_from_image, which zoomed a text-baked card and made the
    letters swim and soften.)"""
    frames = max(1, int(duration * 30))
    # cover-crop at 2× native, then zoompan down to native → supersampled, smooth motion.
    cover2 = (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
              f"crop={W * 2}:{H * 2},setsar=1")
    vf = (f"[0:v]{cover2},"
          f"zoompan=z='min(1.0+0.05*on/{frames},1.05)':d=1:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps=30,setsar=1[bg];"
          f"[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v]")
    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-framerate", "30", "-t", str(duration), "-i", bg_png,  # 0: still bg
        "-i", overlay_png,                                                     # 1: text (static)
        "-stream_loop", "-1", "-i", audio,                                     # 2: music
        "-filter_complex", vf,
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-preset", "slow", "-crf", "16",
        "-maxrate", "12M", "-bufsize", "24M",
        "-c:a", "aac", "-b:a", "192k", "-t", str(duration),
        "-af", f"afade=t=in:st=0:d=1,afade=t=out:st={max(0.0, duration - 1.5):.2f}:d=1.5",
        "-movflags", "+faststart",
        out,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def extract_frame(video, out_png, at=0.8):
    """Grab one representative frame (cropped to 9:16) for color/placement analysis."""
    subprocess.run([
        FFMPEG, "-y", "-ss", str(at), "-i", video,
        "-vf", _COVER, "-frames:v", "1", out_png,
    ], check=True, capture_output=True)
    return out_png


def _duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", path],
                         capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except Exception:
        return 0.0


def make_slowmo(clip, out, target=60.0, max_factor=3.0):
    """Slow the clip down (no reverse) to fill ~target seconds — serene, natural motion.
    Slowdown is capped (max_factor) so it never gets too choppy."""
    dur = _duration(clip) or 12.0
    factor = min(max(target / dur, 1.0), max_factor)
    subprocess.run([
        FFMPEG, "-y", "-i", clip,
        "-vf", f"setpts={factor:.3f}*PTS",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-preset", "fast", "-crf", "16",
        out,
    ], check=True, capture_output=True)
    return out


def make_boomerang(clip, out):
    """Forward + reverse → a seamless loop (~2× the clip length, no jump cut)."""
    subprocess.run([
        FFMPEG, "-y", "-i", clip,
        "-filter_complex", "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]",
        "-map", "[v]", "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-preset", "fast", "-crf", "16",
        out,
    ], check=True, capture_output=True)
    return out


def build_reel(video, overlay_png, audio, out, duration=60):
    """Background video (boomerang, looped/cropped to 9:16) + text overlay + music → MP4."""
    cmd = [
        FFMPEG, "-y",
        "-stream_loop", "-1", "-i", video,        # 0: bg video (loop to fill duration)
        "-i", overlay_png,                         # 1: text overlay (static)
        "-stream_loop", "-1", "-i", audio,         # 2: music (loop to fill)
        "-filter_complex",
        f"[0:v]{_COVER}[bg];[bg][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-preset", "slow", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M",
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
        FFMPEG, "-y",
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
