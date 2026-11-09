#!/usr/bin/env python3
"""Cut highlight clips from videos using ffmpeg scene detection."""
import argparse
import json
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

log = logging.getLogger("clipper")
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}
PTS_RE = re.compile(r"pts_time:(\d+(?:\.\d+)?)")


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def detect_scenes(path: Path, threshold: float) -> list[float]:
    """Return timestamps (seconds) where the scene-change score exceeds threshold."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path),
         "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    # showinfo writes one line per selected frame to stderr
    return [float(m.group(1)) for m in PTS_RE.finditer(proc.stderr)]


def pick_highlights(scenes: list[float], duration: float, clip_length: float, max_clips: int) -> list[float]:
    """Group scene changes that fall within one clip, keep the busiest groups."""
    groups: list[list[float]] = []
    for t in scenes:
        if groups and t - groups[-1][0] < clip_length:
            groups[-1].append(t)
        else:
            groups.append([t])
    busiest = sorted(groups, key=len, reverse=True)[:max_clips]
    starts = sorted(max(0.0, g[0] - 1.0) for g in busiest)
    return [s for s in starts if s + clip_length <= duration]


def cut_clip(src: Path, dst: Path, start: float, length: float, reencode: bool) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", str(src), "-t", f"{length:.2f}"]
    if reencode:
        cmd += ["-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-c", "copy", "-avoid_negative_ts", "make_zero"]
    cmd.append(str(dst))
    subprocess.run(cmd, check=True)


def process_video(src: Path, out_dir: Path, args) -> int:
    duration = probe_duration(src)
    scenes = detect_scenes(src, args.threshold)
    starts = pick_highlights(scenes, duration, args.clip_length, args.max_clips)
    for i, start in enumerate(starts, 1):
        cut_clip(src, out_dir / f"{src.stem}_clip{i:02d}{src.suffix}", start, args.clip_length, args.reencode)
    return len(starts)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_dir", type=Path)
    p.add_argument("output_dir", type=Path)
    p.add_argument("--threshold", type=float, default=0.4, help="scene-change score, 0-1")
    p.add_argument("--clip-length", type=float, default=15.0)
    p.add_argument("--max-clips", type=int, default=5)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--reencode", action="store_true", help="frame-accurate cuts (slower)")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    videos = sorted(f for f in args.input_dir.iterdir() if f.suffix.lower() in VIDEO_EXTS)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_video, v, args.output_dir, args): v for v in videos}
        for fut in as_completed(futures):
            video = futures[fut]
            try:
                log.info("%s: %d clips", video.name, fut.result())
            except subprocess.CalledProcessError as exc:
                log.error("%s failed: %s", video.name, exc)


if __name__ == "__main__":
    main()
