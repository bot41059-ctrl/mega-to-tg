# Copyright (c) 2021 - Present partiallywritten
# Global Callbacks & Task Cancellations

import logging
import asyncio
from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from megadl import CypherClient

logger = logging.getLogger(__name__)


@CypherClient.on_callback_query(filters.regex(r"^cancelqcb-\d+"))
@CypherClient.run_checks
async def cancel_callback(client: CypherClient, query: CallbackQuery):
    """Cancel current downloading/uploading task and clean up."""
    user_id = int(query.data.split("-")[1])
    try:
        client.cancel_user_task(user_id)

        # Cancel any running sub-shell or mega processes
        mg_prc = client.mega_running.get(user_id)
        if mg_prc:
            from megadl.helpers.sysfncs import kill_family
            await kill_family(mg_prc)

        # Clean up files
        dtmp = client.glob_tmp.get(user_id)
        target_path = f"{client.dl_loc}/{user_id}"
        await client.full_cleanup(target_path, user_id)

    except Exception as e:
        logger.warning(f"Error during cancellation: {e}")

    await query.edit_message_text(
        "🛑 **Task Cancelled by User.**\nAll downloads stopped and temporary disk storage was cleared.",
        reply_markup=None,
    )


@CypherClient.on_callback_query(filters.regex(r"^set_chan_seq-\d+"))
@CypherClient.run_checks
async def set_channel_prompt(client: CypherClient, query: CallbackQuery):
    """Interactive prompt to set target channel."""
    user_id = int(query.data.split("-")[1])
    chat_id = query.message.chat.id

    msg = await client.ask(
        chat_id,
        "📢 **Enter Target Channel ID or Username:**\n\n"
        "Example:\n"
        "• `@MyAwesomeChannel`\n"
        "• `-1001234567890`\n\n"
        "*(Make sure the bot has been added to the channel as an Admin with Post Messages permission!)*"
    )

    if not msg or not msg.text:
        return await client.send_message(chat_id, "⚠️ No channel provided. Process cancelled.")

    chan_input = msg.text.strip()
    client.set_channel(chan_input)

    await client.send_message(
        chat_id,
        f"✅ **Target Channel set to:** `{client.channel_id}`\n\n"
        "Now send your MEGA link again or restart the upload!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Upload to Channel", callback_data=f"start_seq_chan-{user_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancelqcb-{user_id}")]
        ])
    )
