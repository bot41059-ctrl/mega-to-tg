# Copyright (c) 2021 - Present partiallywritten
# Video metadata and thumbnail extraction helper

import os
import shutil
import asyncio
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


async def get_video_metadata(file_path: str) -> Tuple[int, int, int]:
    """
    Returns (duration_seconds, width, height) of a video file.
    Uses ffprobe if available.
    """
    duration = 0
    width = 0
    height = 0

    if not shutil.which("ffprobe"):
        return duration, width, height

    # 1. Get duration
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        out_str = stdout.decode().strip()
        if out_str:
            duration = int(float(out_str))
    except Exception as e:
        logger.debug(f"ffprobe duration error: {e}")

    # 2. Get width and height
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        out_str = stdout.decode().strip()
        if out_str and "x" in out_str:
            w_str, h_str = out_str.split("x")[:2]
            width = int(w_str)
            height = int(h_str)
    except Exception as e:
        logger.debug(f"ffprobe dimensions error: {e}")

    return duration, width, height


async def generate_thumbnail(
    file_path: str, output_thumb_path: str, duration: int = 0
) -> Optional[str]:
    """
    Generates a JPEG thumbnail for a video file at ~10% timestamp using ffmpeg.
    """
    if not shutil.which("ffmpeg"):
        return None

    try:
        # Pick screenshot time
        seek_time = max(1, int(duration * 0.1)) if duration > 0 else 5
        os.makedirs(os.path.dirname(output_thumb_path), exist_ok=True)

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-ss", str(seek_time), "-i", file_path,
            "-vframes", "1", "-q:v", "2", output_thumb_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        if os.path.exists(output_thumb_path) and os.path.getsize(output_thumb_path) > 0:
            return output_thumb_path
    except Exception as e:
        logger.debug(f"ffmpeg thumbnail generation failed: {e}")

    return None
