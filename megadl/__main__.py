# Copyright (c) 2021 - Present partiallywritten
# Author: https://github.com/partiallywritten
# Project: https://github.com/partiallywritten/Mega.nz-Bot
# Description: __main__.py

from pyrogram import idle
from . import CypherClient

if __name__ == "__main__":
    print("> Starting Telegram Bot Client...")
    CypherClient.start()
    bot_me = CypherClient.get_me()
    print("=" * 50)
    print(f"🤖 Bot Started Successfully as @{bot_me.username} ({bot_me.first_name})")
    print(f"📢 Target Channel: {CypherClient.channel_id or 'Not Set (use /setchannel)'}")
    print("✨ Bot is active and listening for MEGA links!")
    print("=" * 50)
    idle()
    print("\n> Stopping Bot Client...")
    CypherClient.stop()
    print("✅ Bot stopped cleanly.")
