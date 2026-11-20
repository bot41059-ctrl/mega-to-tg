# Copyright (c) 2021 - Present partiallywritten
# Visual Progress Bars & Speed Metrics for Telegram Messages

import time
from typing import Optional
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def format_bytes(b: float) -> str:
    """Format bytes into readable string with unit."""
    val = float(b)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024:
            return f"{val:.2f} {unit}"
        val /= 1024
    return f"{val:.2f} PB"


def format_time(seconds: float) -> str:
    """Format seconds into readable time string."""
    seconds = int(max(seconds, 0))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def build_progress_bar(percentage: float, length: int = 12) -> str:
    """
    Renders a visual progress bar.
    Example: [██████░░░░░░] 50.0%
    """
    pct = max(0.0, min(100.0, percentage))
    filled_len = int(round(length * pct / 100.0))
    bar = "█" * filled_len + "░" * (length - filled_len)
    return f"[{bar}] {pct:.1f}%"


def create_status_card(
    phase_title: str,
    current: int,
    total: int,
    speed: float,
    eta: float,
    filename: str,
    rel_path: str,
    index: int,
    total_files: int,
    destination: str,
) -> str:
    """
    Generates a visual card for download and upload status.
    Shows downloaded/uploaded bytes, total size, speed, ETA, and progress bar.
    """
    pct = (current * 100.0 / total) if total > 0 else 0.0
    bar = build_progress_bar(pct, length=12)

    return (
        f"{phase_title} `[{index}/{total_files}]`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 **File:** `{filename}`\n"
        f"📂 **Path:** `{rel_path}`\n"
        f"🎯 **Target:** `{destination}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{bar}\n"
        f"📊 **Progress:** `{format_bytes(current)}` / `{format_bytes(total)}` (`{pct:.1f}%`)\n"
        f"⚡ **Speed:** `{format_bytes(speed)}/s`\n"
        f"⏳ **ETA:** `{format_time(eta)}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🧹 *Auto-cleans local storage after upload*"
    )


async def track_upload_progress(
    current: int,
    total: int,
    client,
    chat_id: int,
    msg_id: int,
    start_time: float,
    filename: str = "",
    rel_path: str = "",
    index: int = 1,
    total_files: int = 1,
    destination: str = "",
    user_id: Optional[int] = None,
    last_update_dict: Optional[dict] = None,
):
    """
    Real-time progress callback for Telegram uploads.
    Updates every 3.5 seconds with exact speed, bytes transferred, and ETA.
    """
    now = time.time()
    if last_update_dict is None:
        last_update_dict = {"last_time": 0.0}

    last_time = last_update_dict.get("last_time", 0.0)

    # Update only if 3.5s passed or upload completed
    if (now - last_time >= 3.5) or (current >= total):
        last_update_dict["last_time"] = now
        diff = max(now - start_time, 0.001)
        speed = current / diff
        eta = (total - current) / speed if speed > 0 else 0.0

        pmsg = create_status_card(
            phase_title="📤 **UPLOADING TO TELEGRAM**",
            current=current,
            total=total,
            speed=speed,
            eta=eta,
            filename=filename,
            rel_path=rel_path,
            index=index,
            total_files=total_files,
            destination=str(destination),
        )

        reply_markup = None
        if user_id:
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel Task", callback_data=f"cancelqcb-{user_id}")]
            ])

        try:
            await client.edit_message_text(chat_id, msg_id, pmsg, reply_markup=reply_markup)
        except MessageNotModified:
            pass
        except FloodWait as fw:
            last_update_dict["last_time"] = now + fw.value
        except Exception:
            pass


async def track_progress(current, total, client, chat_id: int, msg_id: int, start: float, **kwargs):
    """Legacy alias for backward compatibility."""
    await track_upload_progress(
        current=current,
        total=total,
        client=client,
        chat_id=chat_id,
        msg_id=msg_id,
        start_time=start,
    )
