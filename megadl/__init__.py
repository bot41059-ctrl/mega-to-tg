# Copyright (c) 2021 - Present partiallywritten
# Author: https://github.com/partiallywritten
# Project: https://github.com/partiallywritten/Mega.nz-Bot
# Description: __init__.py

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Ensure event loop exists on Python 3.10+ before pyrogram import
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Setup clean logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

print("=" * 50)
print("🚀 MEGA to Telegram Bot - Sequential Downloader")
print("=" * 50)

# uvloop integration for Unix-like systems (Linux / Colab)
if sys.platform != "win32":
    try:
        import uvloop
        uvloop.install()
        print("⚡ uvloop enabled for high-performance asyncio")
    except ImportError:
        pass

# Loading environment variables
if os.path.isfile(".env"):
    load_dotenv()
    print("✅ Configuration loaded from .env file")
else:
    print("ℹ️ No .env file found; using environment variables directly")

# Initialize Client
from .helpers.cypher import MeganzClient
CypherClient: "MeganzClient" = MeganzClient()
