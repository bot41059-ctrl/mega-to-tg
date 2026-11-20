# Copyright (c) 2021 - Present partiallywritten
# General Commands: /start, /help, /setchannel, /channel, /status, /cancel

import os
import shutil
import psutil
from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from megadl import CypherClient
from megadl.lib.mega_scanner import format_size


@CypherClient.on_message(filters.command("start"))
@CypherClient.run_checks
async def start_msg(client: CypherClient, msg: Message):
    user_name = msg.from_user.first_name if msg.from_user else "Friend"
    channel_info = f"`{client.channel_id}`" if client.channel_id else "_Not Set (use /setchannel)_"

    welcome_text = (
        f"👋 **Namaste {user_name}! Welcome to Mega-to-Telegram Bot** 🎬\n\n"
        "Main aapke MEGA shared folder ko recursively scan karke, saare subfolders "
        "aur unke videos ko **ek-ek karke download aur upload** kar sakta hu Telegram Channel pe!\n\n"
        "✨ **Key Features:**\n"
        "• 🔍 **Deep Scanner:** Folder ke andar kitni bhi subfolders ho, sabko scan karega!\n"
        "• 🌳 **Hierarchy Tree:** Complete folders & video count ka beautiful tree report dikhayega.\n"
        "• ⚡ **One-by-One Transfer:** Ek video download -> Channel pe upload -> Colab disk se turant delete!\n"
        "• 💾 **Colab Safe:** Disk space kabhi full nahi hogi (no out-of-disk crashes)!\n"
        "• 🎬 **Rich Video Post:** Thumbnail, Duration, Streaming support, and clean captions!\n"
        "• 🔪 **Auto-Splitter:** 2GB se bade videos ko automatically split karke bhejega.\n\n"
        f"📢 **Current Target Channel:** {channel_info}\n\n"
        "💡 **Bas koi bhi MEGA link yaha send karo aur magic dekho!**"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Set Target Channel", callback_data=f"set_chan_seq-{msg.from_user.id}"),
            InlineKeyboardButton("ℹ️ Help & Commands", callback_data="help_btn"),
        ]
    ])

    await msg.reply_text(welcome_text, reply_markup=buttons, disable_web_page_preview=True)


@CypherClient.on_callback_query(filters.regex(r"^help_btn$"))
async def help_callback(client: CypherClient, query):
    await query.message.reply_text(
        "📖 **Help & Commands Guide:**\n\n"
        "1. **Send Link:** Bas koi bhi public MEGA folder ya file ka link paste karein.\n"
        "2. **Bot Scans:** Bot pehle sabhi folders aur videos ko scan karega aur tree report dega.\n"
        "3. **Start Upload:** Button click karte hi ek-ek karke video download aur channel pe upload shuru ho jayega!\n\n"
        "🛠 **Commands:**\n"
        "• `/setchannel <channel_id_or_username>` - Set target channel\n"
        "• `/channel` - View current channel\n"
        "• `/cancel` - Stop active download/upload task\n"
        "• `/status` - Check Colab system & disk status\n"
        "• `/help` - Show this guide"
    )
    await query.answer()


@CypherClient.on_message(filters.command("help"))
@CypherClient.run_checks
async def help_msg(client: CypherClient, msg: Message):
    await msg.reply_text(
        "📖 **Mega to Telegram Bot - Help & Instructions**\n\n"
        "🔹 **Kaise use karein?**\n"
        "1. Sabse pehle bot ko apne Telegram Channel me **Admin** banayein jisme **Post Messages** permission on ho.\n"
        "2. Bot ko channel bataiye: `/setchannel @YourChannelUsername` ya `/setchannel -1001234567890`\n"
        "3. MEGA folder ka link bot ko send karein.\n"
        "4. Bot scan karke total subfolders, total videos aur size batayega.\n"
        "5. **🚀 Upload All Videos** pe click karein. Bot ek-ek video download karega, channel pe post karega, aur Colab storage clean karta rahega!\n\n"
        "🛠 **Useful Commands:**\n"
        "• `/setchannel <channel>` - Channel set karein\n"
        "• `/channel` - Current channel dekhein\n"
        "• `/cancel` - Chal rahe download/upload ko cancel karein\n"
        "• `/status` - System RAM aur Disk space check karein"
    )


@CypherClient.on_message(filters.command("setchannel"))
@CypherClient.run_checks
async def set_channel_cmd(client: CypherClient, msg: Message):
    parts = msg.text.split(None, 1)
    if len(parts) < 2:
        return await msg.reply(
            "⚠️ **Format:** `/setchannel <channel_id_or_username>`\n\n"
            "Example:\n"
            "• `/setchannel @MyAnimeChannel`\n"
            "• `/setchannel -1001928374650`"
        )

    chan_input = parts[1].strip()
    client.set_channel(chan_input)

    # Test permissions
    try:
        test = await client.send_message(
            client.channel_id,
            "🤖 **Mega to Telegram Bot connected successfully!**"
        )
        await test.delete()
        await msg.reply(f"✅ **Success! Target channel set to:** `{client.channel_id}`")
    except Exception as e:
        await msg.reply(
            f"⚠️ **Target channel set to `{client.channel_id}`, lekin bot waha message send nahi kar paya!**\n\n"
            f"Kripya check karein ki bot channel me **Admin** hai ya nahi.\n`Error: {e}`"
        )


@CypherClient.on_message(filters.command("channel"))
@CypherClient.run_checks
async def get_channel_cmd(client: CypherClient, msg: Message):
    if client.channel_id:
        await msg.reply(f"📢 **Current Target Channel:** `{client.channel_id}`")
    else:
        await msg.reply("⚠️ **Target channel set nahi hai!**\nUse: `/setchannel <channel_id_or_username>`")


@CypherClient.on_message(filters.command("cancel"))
@CypherClient.run_checks
async def cancel_cmd(client: CypherClient, msg: Message):
    user_id = msg.from_user.id if msg.from_user else msg.chat.id
    client.cancel_user_task(user_id)
    await client.full_cleanup(f"{client.dl_loc}/{user_id}", user_id)
    await msg.reply("🛑 **Active process cancelled!** All downloads stopped and disk cleaned.")


@CypherClient.on_message(filters.command("status"))
@CypherClient.run_checks
async def status_cmd(client: CypherClient, msg: Message):
    # Disk usage
    total, used, free = shutil.disk_usage(client.dl_loc)
    # Memory usage
    mem = psutil.virtual_memory()

    status_text = (
        "📊 **Google Colab / System Status:**\n\n"
        f"💾 **Disk Storage:**\n"
        f"  • Total: `{format_size(total)}`\n"
        f"  • Used: `{format_size(used)}`\n"
        f"  • Free: `{format_size(free)}`\n\n"
        f"🧠 **RAM Memory:**\n"
        f"  • Used: `{format_size(mem.used)}` / `{format_size(mem.total)}` ({mem.percent}%)\n\n"
        f"⚙️ **Active Tasks:** `{len(client.active_tasks)}`\n"
        f"📢 **Channel Target:** `{client.channel_id or 'None'}`"
    )
    await msg.reply(status_text)
