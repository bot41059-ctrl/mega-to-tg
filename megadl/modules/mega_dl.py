# Copyright (c) 2021 - Present partiallywritten
# Enhanced Recursive Scanner, Sequential Downloader & Channel Uploader

import os
import time
import asyncio
import logging
from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from pyrogram.errors import FloodWait, MessageNotModified

from megadl import CypherClient
from megadl.lib.mega_scanner import MegaScanner, format_size
from megadl.lib.mega_downloader import MegaDownloader
from megadl.helpers.video_processor import (
    get_video_metadata,
    generate_thumbnail,
    format_duration,
)
from megadl.helpers.pyros import (
    build_progress_bar,
    format_time,
    format_bytes,
    create_status_card,
    track_upload_progress,
)
from megadl.helpers.files import splitit, fs_cleanup, listfiles

logger = logging.getLogger(__name__)


@CypherClient.on_message(filters.regex(r"https?:\/\/mega\.(?:nz|co\.nz)\/(?:folder|file|#).+"))
@CypherClient.run_checks
async def dl_from(client: CypherClient, msg: Message):
    """
    Handle MEGA link sent by user.
    Scans the link, extracts folder hierarchy and video list, and presents options.
    """
    user_id = msg.from_user.id if msg.from_user else msg.chat.id
    url = msg.text.strip()

    status_msg = await msg.reply(
        "🔍 **Scanning MEGA Link...**\n"
        "Analyzing folder structure, subdirectories, and video files. Please wait a moment...",
        reply_to_message_id=msg.id,
    )

    try:
        scan_data = await MegaScanner.scan(url)
    except Exception as e:
        logger.error(f"Scan error: {e}", exc_info=True)
        return await status_msg.edit_text(f"❌ **Failed to scan MEGA link:**\n`{e}`")

    # Save scan data in client's temporary cache for this user
    client.glob_tmp[user_id] = scan_data
    client.clear_user_task(user_id)

    # If it's a single file
    if not scan_data["is_folder"]:
        btn_list = []
        if client.channel_id:
            btn_list.append([
                InlineKeyboardButton(
                    f"📢 Upload to Channel ({client.channel_id})",
                    callback_data=f"dl_single_chan-{user_id}"
                )
            ])
        btn_list.append([
            InlineKeyboardButton("💬 Upload to this Chat", callback_data=f"dl_single_chat-{user_id}")
        ])
        btn_list.append([
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancelqcb-{user_id}")
        ])

        caption = (
            "📄 **MEGA File Found!**\n\n"
            f"🎬 **Name:** `{scan_data['name']}`\n"
            f"💾 **Size:** `{scan_data['size_str']}`\n"
            f"🎥 **Type:** {'Video 🎬' if scan_data['is_video'] else 'Document 📁'}\n\n"
            "Select destination to download and upload:"
        )
        return await status_msg.edit_text(caption, reply_markup=InlineKeyboardMarkup(btn_list))

    # If it's a folder
    total_videos = scan_data["total_videos"]
    total_folders = scan_data["total_folders"]
    root_name = scan_data["root_name"]
    total_size = scan_data["total_video_size_str"]

    if total_videos == 0:
        return await status_msg.edit_text(
            f"📁 **Root Folder:** `{root_name}`\n"
            f"📂 **Subfolders Found:** `{total_folders}`\n\n"
            "⚠️ **No video files found inside this folder or its subfolders!**\n"
            "This bot is configured to download and upload videos."
        )

    btn_list = []
    if client.channel_id:
        btn_list.append([
            InlineKeyboardButton(
                f"🚀 Upload All Videos to Channel",
                callback_data=f"start_seq_chan-{user_id}"
            )
        ])
    else:
        btn_list.append([
            InlineKeyboardButton(
                "📢 Set Channel & Upload",
                callback_data=f"set_chan_seq-{user_id}"
            )
        ])

    btn_list.append([
        InlineKeyboardButton(
            "💬 Upload All Videos to this Chat",
            callback_data=f"start_seq_chat-{user_id}"
        )
    ])
    btn_list.append([
        InlineKeyboardButton(
            "📋 View Video List",
            callback_data=f"view_vids-{user_id}"
        ),
        InlineKeyboardButton(
            "❌ Cancel",
            callback_data=f"cancelqcb-{user_id}"
        )
    ])

    report_text = (
        "📁 **MEGA Folder Scan Completed!**\n\n"
        f"🏷 **Main Folder:** `{root_name}`\n"
        f"📂 **Total Subfolders:** `{total_folders}`\n"
        f"🎬 **Total Videos Found:** `{total_videos}`\n"
        f"💾 **Total Videos Size:** `{total_size}`\n"
        f"📄 **Other Files:** `{scan_data['total_other']}`\n\n"
        f"🌳 **Hierarchy Preview:**\n"
        f"```\n{scan_data['tree_text']}\n```\n\n"
        "⚡ *Videos will be downloaded and uploaded one-by-one to preserve Colab storage!*"
    )

    await status_msg.edit_text(
        report_text,
        reply_markup=InlineKeyboardMarkup(btn_list)
    )


@CypherClient.on_callback_query(filters.regex(r"^view_vids-\d+"))
@CypherClient.run_checks
async def view_videos_callback(client: CypherClient, query: CallbackQuery):
    """Display list of discovered video files."""
    user_id = int(query.data.split("-")[1])
    scan_data = client.glob_tmp.get(user_id)

    if not scan_data or not scan_data.get("videos"):
        return await query.answer("No scan data found. Please send the MEGA link again.", show_alert=True)

    videos = scan_data["videos"]
    lines = [f"📋 **Discovered Videos ({len(videos)} files):**\n"]
    for i, v in enumerate(videos[:30], 1):
        lines.append(f"{i}. `{v['n']}` ({v['size_str']})")

    if len(videos) > 30:
        lines.append(f"\n... and {len(videos) - 30} more videos.")

    await query.message.reply("\n".join(lines))
    await query.answer()


@CypherClient.on_callback_query(filters.regex(r"^(start_seq_chan|start_seq_chat|dl_single_chan|dl_single_chat)-\d+"))
@CypherClient.run_checks
async def start_transfer_callback(client: CypherClient, query: CallbackQuery):
    """
    Handle initiating sequential transfer to Channel or current Chat.
    """
    action, uid_str = query.data.split("-")
    user_id = int(uid_str)
    scan_data = client.glob_tmp.get(user_id)

    if not scan_data:
        return await query.edit_message_text("⚠️ **Session expired.** Please send the MEGA link again.")

    # Determine destination chat
    if "chan" in action:
        if not client.channel_id:
            return await query.edit_message_text(
                "⚠️ **Target Channel not set!**\n"
                "Please configure a channel using `/setchannel <channel_id_or_username>`\n"
                "or click 'Upload to this Chat' instead."
            )
        target_chat = client.channel_id
    else:
        target_chat = query.message.chat.id

    # Test permissions if channel
    if "chan" in action:
        try:
            test_msg = await client.send_message(
                target_chat,
                f"🚀 **Starting Mega-to-Telegram Task**\nSource: `{scan_data.get('root_name') or scan_data.get('name')}`"
            )
            await test_msg.delete()
        except Exception as e:
            return await query.edit_message_text(
                f"❌ **Channel Error:** Could not access target channel `{target_chat}`.\n"
                f"Make sure the bot is an **Admin** in the channel with **Post Messages** permission!\n\n`{e}`"
            )

    client.clear_user_task(user_id)
    progress_msg = await query.edit_message_text(
        "🚀 **Task Initialized!**\nPreparing sequential download and upload queue...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Task", callback_data=f"cancelqcb-{user_id}")]
        ])
    )

    # Launch task in background
    task = asyncio.create_task(
        run_sequential_process(client, user_id, scan_data, target_chat, progress_msg)
    )
    client.active_tasks[user_id] = task


async def run_sequential_process(
    client: CypherClient,
    user_id: int,
    scan_data: dict,
    target_chat: any,
    progress_msg: Message
):
    """
    Sequentially processes each video:
    1. Downloads 1 video from MEGA (with live download speed & downloaded/total bytes)
    2. Generates thumbnail & metadata
    3. Uploads to Telegram channel / chat (with live upload speed & uploaded/total bytes)
    4. Immediately deletes local video and thumbnail from disk!
    5. Repeats for next video
    """
    is_folder = scan_data.get("is_folder", False)
    videos = scan_data.get("videos", []) if is_folder else [scan_data]
    total_videos = len(videos)
    download_folder = os.path.join(client.dl_loc, str(user_id))
    os.makedirs(download_folder, exist_ok=True)

    uploaded_count = 0
    total_bytes_transferred = 0

    try:
        for idx, video in enumerate(videos, 1):
            # 1. Check if user cancelled
            if client.is_user_cancelled(user_id):
                await progress_msg.edit_text("🛑 **Task was cancelled by the user.**")
                break

            video_name = video.get("n") or video.get("name")
            video_size = video.get("s") or video.get("size", 0)
            video_size_str = video.get("size_str", format_size(video_size))
            video_path = video.get("rel_path", video_name)

            # Update initial status
            init_dl_card = create_status_card(
                phase_title="📥 **DOWNLOADING FROM MEGA**",
                current=0,
                total=video_size,
                speed=0.0,
                eta=0.0,
                filename=video_name,
                rel_path=video_path,
                index=idx,
                total_files=total_videos,
                destination=str(target_chat),
            )

            await progress_msg.edit_text(
                init_dl_card,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel Task", callback_data=f"cancelqcb-{user_id}")]
                ])
            )

            # 2. Download progress callback
            last_dl_update = {"time": time.time()}

            async def dl_progress(downloaded, total, speed, eta, filename):
                now = time.time()
                if now - last_dl_update["time"] >= 3.0 or downloaded >= total:
                    last_dl_update["time"] = now
                    card_text = create_status_card(
                        phase_title="📥 **DOWNLOADING FROM MEGA**",
                        current=downloaded,
                        total=total,
                        speed=speed,
                        eta=eta,
                        filename=filename,
                        rel_path=video_path,
                        index=idx,
                        total_files=total_videos,
                        destination=str(target_chat),
                    )
                    try:
                        await progress_msg.edit_text(
                            card_text,
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("❌ Cancel Task", callback_data=f"cancelqcb-{user_id}")]
                            ])
                        )
                    except (MessageNotModified, FloodWait):
                        pass

            # 3. Download the file from MEGA
            downloaded_file_path = None
            try:
                downloaded_file_path = await MegaDownloader.download_node(
                    node=video,
                    dest_dir=download_folder,
                    progress_callback=dl_progress,
                    cancel_check=lambda: client.is_user_cancelled(user_id),
                )
            except asyncio.CancelledError:
                await progress_msg.edit_text("🛑 **Download cancelled.** Cleaned up local files.")
                break
            except Exception as e:
                logger.error(f"Download failed for {video_name}: {e}", exc_info=True)
                await progress_msg.edit_text(f"⚠️ **Error downloading {video_name}:** `{e}`\nSkipping to next video...")
                await asyncio.sleep(4)
                continue

            if client.is_user_cancelled(user_id):
                if downloaded_file_path and os.path.exists(downloaded_file_path):
                    os.remove(downloaded_file_path)
                await progress_msg.edit_text("🛑 **Task was cancelled.**")
                break

            # 4. Extract metadata & generate thumbnail
            duration, width, height = await get_video_metadata(downloaded_file_path)
            thumb_path = os.path.join(client.tmp_loc, f"thumb_{user_id}_{idx}.jpg")
            thumb = await generate_thumbnail(downloaded_file_path, thumb_path, duration)

            # 5. Prepare Telegram caption
            caption = (
                f"🎬 **{video_name}**\n\n"
                f"📂 **Path:** `{video_path}`\n"
                f"💾 **Size:** `{video_size_str}`\n"
                f"⏱ **Duration:** `{format_duration(duration)}`\n"
                f"📊 **Index:** Video {idx} of {total_videos}\n\n"
                "🤖 *Uploaded via Mega to Telegram Bot*"
            )

            # 6. Upload to Telegram with live upload speed and bytes transferred
            actual_file_size = os.path.getsize(downloaded_file_path)

            init_up_card = create_status_card(
                phase_title="📤 **UPLOADING TO TELEGRAM**",
                current=0,
                total=actual_file_size,
                speed=0.0,
                eta=0.0,
                filename=video_name,
                rel_path=video_path,
                index=idx,
                total_files=total_videos,
                destination=str(target_chat),
            )

            await progress_msg.edit_text(
                init_up_card,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel Task", callback_data=f"cancelqcb-{user_id}")]
                ])
            )

            upload_start_time = time.time()
            last_up_dict = {"last_time": upload_start_time}

            async def up_progress(current, total):
                await track_upload_progress(
                    current=current,
                    total=total,
                    client=client,
                    chat_id=progress_msg.chat.id,
                    msg_id=progress_msg.id,
                    start_time=upload_start_time,
                    filename=video_name,
                    rel_path=video_path,
                    index=idx,
                    total_files=total_videos,
                    destination=str(target_chat),
                    user_id=user_id,
                    last_update_dict=last_up_dict,
                )

            try:
                if actual_file_size > client.mx_size:
                    # File larger than 2GB, split into parts
                    await progress_msg.edit_text(
                        f"🔪 **Video [{idx}/{total_videos}] exceeds 2GB!**\n"
                        f"Splitting `{video_name}` into chunks under 2GB..."
                    )
                    split_dir = os.path.join(download_folder, f"split_{idx}")
                    await splitit(downloaded_file_path, split_dir, client.mx_size, client.splt_buffer)
                    split_files = listfiles(split_dir)

                    for part_idx, sfile in enumerate(split_files, 1):
                        part_caption = f"{caption}\n🧩 **Part {part_idx}/{len(split_files)}**"
                        await client.send_document(
                            chat_id=target_chat,
                            document=sfile,
                            caption=part_caption,
                            progress=up_progress,
                        )
                    fs_cleanup(split_dir)
                else:
                    # Native Video Upload with thumbnail & duration
                    await client.send_video(
                        chat_id=target_chat,
                        video=downloaded_file_path,
                        caption=caption,
                        duration=duration,
                        width=width,
                        height=height,
                        thumb=thumb,
                        supports_streaming=True,
                        progress=up_progress,
                    )

                uploaded_count += 1
                total_bytes_transferred += actual_file_size

            except Exception as e:
                logger.error(f"Upload failed for {video_name}: {e}", exc_info=True)
                await progress_msg.edit_text(f"⚠️ **Upload failed for {video_name}:** `{e}`\nProceeding to next video...")
                await asyncio.sleep(4)

            finally:
                # 7. CRITICAL DISK CLEANUP: Delete local copy immediately!
                if downloaded_file_path and os.path.exists(downloaded_file_path):
                    try:
                        os.remove(downloaded_file_path)
                    except Exception:
                        pass
                if thumb and os.path.exists(thumb):
                    try:
                        os.remove(thumb)
                    except Exception:
                        pass

            # Update progress message after video completion
            await progress_msg.edit_text(
                f"✅ **[{idx}/{total_videos}] Uploaded & Cleaned from Disk!**\n"
                f"📄 `{video_name}` ({video_size_str})\n"
                f"💾 Local disk freed. Next video starting in 3 seconds..."
            )
            await asyncio.sleep(2.5)

        # 8. All done
        if not client.is_user_cancelled(user_id):
            await progress_msg.edit_text(
                "🎉 **All Videos Successfully Uploaded!**\n\n"
                f"🎬 **Total Videos Uploaded:** `{uploaded_count}/{total_videos}`\n"
                f"🎯 **Destination:** `{target_chat}`\n"
                f"💾 **Total Transferred:** `{format_size(total_bytes_transferred)}`\n"
                "🧹 **All temporary local files have been wiped from disk!**"
            )

    except asyncio.CancelledError:
        await progress_msg.edit_text("🛑 **Process stopped and cleaned up.**")
    except Exception as e:
        logger.error(f"Sequential processing error: {e}", exc_info=True)
        await progress_msg.edit_text(f"❌ **An error occurred during task:**\n`{e}`")
    finally:
        client.clear_user_task(user_id)
        fs_cleanup(download_folder)
