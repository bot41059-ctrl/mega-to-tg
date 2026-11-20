# Copyright (c) 2021 - Present partiallywritten
# Author: https://github.com/partiallywritten
# Project: https://github.com/partiallywritten/Mega.nz-Bot
# Description: Custom pyrogram client useful methods

import os
import json
import asyncio
import logging
import requests
import functools

from typing import Callable
from asyncio import sleep as xsleep
from cryptography.fernet import Fernet

from pyrogram import Client, errors
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message, CallbackQuery

from .database import CypherDB
from .sysfncs import run_on_shell, kill_family
from .files import send_as_guessed, fs_cleanup, splitit, listfiles

_emsg = """
##### Mega.nz-Bot Error Handler #####

Raised by: {}
Version: {}
Module: {}
Error:
{}
"""


class MeganzClient(Client):
    """
    Custom pyrogram client for Mega.nz-Bot with Sequential Downloader & Channel Uploader
    """

    version = "2.1.0"
    dl_loc = None
    tmp_loc = None
    database = CypherDB() if os.getenv("MONGO_URI") else None

    def __init__(self):
        print("> Setting up file locations")
        self.cwd = os.getcwd()
        if os.getenv("USE_ENV") in ["True", "true"] or not os.getenv("DOWNLOAD_LOCATION"):
            self.dl_loc = f"{self.cwd}/downloads"
        else:
            self.dl_loc = os.getenv("DOWNLOAD_LOCATION")

        self.tmp_loc = f"{self.dl_loc}/temps"
        self.mx_size = int(os.getenv("TG_MAX_SIZE", 2040108421))
        self.splt_buffer = int(os.getenv("SPLITTER_BUFFER_SIZE", 1048576))

        os.makedirs(self.dl_loc, exist_ok=True)
        os.makedirs(self.tmp_loc, exist_ok=True)

        # Telegram Channel ID
        raw_chan = os.getenv("CHANNEL_ID", "").strip()
        if raw_chan:
            if raw_chan.startswith("-100") and raw_chan.lstrip("-").isdigit():
                self.channel_id = int(raw_chan)
            elif raw_chan.lstrip("-").isdigit():
                self.channel_id = int(f"-100{raw_chan}")
            else:
                self.channel_id = raw_chan
        else:
            self.channel_id = None

        # Initializing pyrogram client
        print("> Initializing client")
        api_id = os.getenv("APP_ID") or os.getenv("API_ID")
        api_hash = os.getenv("API_HASH")
        bot_token = os.getenv("BOT_TOKEN")

        super().__init__(
            "MegaBotCypher",
            bot_token=bot_token,
            api_id=int(api_id) if api_id and str(api_id).isdigit() else api_id,
            api_hash=api_hash,
            plugins=dict(root="megadl/modules"),
            sleep_threshold=15,
        )

        self.glob_tmp = {}
        self.environs = os.environ.copy()
        self.active_tasks = {}
        self.cancelled_users = set()

        print("> Updating privacy settings")
        _auths = os.getenv("AUTH_USERS", "*")
        self.auth_users = (
            {"*"}
            if not _auths or _auths.strip() == "*"
            else set(map(int, _auths.split()))
            if not _auths.startswith("*")
            else {"*"}
        )
        log_chat = os.getenv("LOG_CHAT")
        self.log_chat = int(log_chat) if log_chat and log_chat != "-1001234567890" else None
        self.use_logs = {"dl_from", "up_to"}
        self.req_db_fn = {"mega_logger", "mega_logoutter", "set_user_proxy"}
        self.is_public = True if self.database else False

        # Key encryption handling
        key_loc = f"{os.getcwd()}/cipher.key"
        if os.path.isfile(key_loc):
            with open(key_loc, "r") as f:
                self.cipher = Fernet(f.read().strip().encode())
        elif os.getenv("CYPHER_KEY"):
            self.cipher = Fernet(os.getenv("CYPHER_KEY").strip().encode())
        else:
            # Generate temporary random key in RAM so bot never crashes
            self.cipher = Fernet(Fernet.generate_key())

        # Check for updates safely
        try:
            remote_updates = requests.get(
                "https://raw.githubusercontent.com/partiallywritten/Mega.nz-Bot/main/updates.json",
                timeout=5,
            ).json()
            if os.path.exists("updates.json"):
                with open("updates.json", "r") as f:
                    local_updates = json.load(f)
                    if remote_updates.get("commit") != local_updates.get("commit"):
                        print("    |> Update available!")
        except Exception:
            pass

        print("> Setting up additional functions")
        self.listening = {}
        self.mega_running = {}
        self.ddl_running = {}
        self.add_handler(MessageHandler(self.use_listner))

    def set_channel(self, channel_input: str):
        """Set or update default channel for uploads."""
        ch = str(channel_input).strip()
        if ch.startswith("-100") and ch.lstrip("-").isdigit():
            self.channel_id = int(ch)
        elif ch.lstrip("-").isdigit():
            self.channel_id = int(f"-100{ch}")
        else:
            self.channel_id = ch

    def cancel_user_task(self, user_id: int):
        """Mark task as cancelled for a user."""
        self.cancelled_users.add(user_id)
        task = self.active_tasks.get(user_id)
        if task and not task.done():
            task.cancel()

    def is_user_cancelled(self, user_id: int) -> bool:
        """Check if user has requested cancellation."""
        return user_id in self.cancelled_users

    def clear_user_task(self, user_id: int):
        """Clear task and cancellation flag."""
        self.cancelled_users.discard(user_id)
        self.active_tasks.pop(user_id, None)

    def run_checks(self, func) -> Callable:
        """Decorator to run middleware checks."""
        async def cy_run(client: Client, msg: Message | CallbackQuery):
            uid = msg.from_user.id if msg.from_user else 0

            try:
                _func_name = func.__name__
                if _func_name in self.use_logs:
                    if uid in self.mega_running or uid in self.ddl_running or uid in self.active_tasks:
                        return await msg.reply(
                            "⚠️ **You already have an active process running!**\n"
                            "Please wait until it completes or use `/cancel` to stop it."
                        )
                    if self.log_chat:
                        try:
                            _frwded = await msg.forward(chat_id=self.log_chat)
                            await _frwded.reply(
                                f"**#PROCESS_LOG** \n\n**From:** `{uid}`"
                            )
                        except Exception:
                            pass

                # Check auth users
                if self.database:
                    status = await self.database.add(uid)
                    if status and status.get("banned"):
                        return await self.cyeor(
                            msg,
                            f"**You are banned from using this bot.**\nReason: `{status.get('reason')}`",
                            True,
                        )

                can_use = ("*" in self.auth_users) or (uid in self.auth_users)
                if not can_use:
                    await self.cyeor(
                        msg,
                        "⛔ **Access Denied:** You are not authorized to use this bot.",
                        True,
                    )
                    return msg.stop_propagation()

                return await func(client, msg)

            except errors.FloodWait as e:
                await xsleep(e.value)
                return await func(client, msg)
            except errors.MessageNotModified:
                pass
            except asyncio.CancelledError:
                pass
            except Exception as e:
                await self.cyeor(msg, f"❌ **Error occurred:**\n`{e}`")
                await self.full_cleanup(f"{self.dl_loc}/{uid}", uid)
                logging.warning(_emsg.format(func.__name__, self.version, func.__module__, e))

        return cy_run

    async def cyeor(
        self, msg: Message | CallbackQuery, text: str, reply: bool = False, **kwargs
    ):
        """Edit or reply to Message / CallbackQuery safely."""
        try:
            if isinstance(msg, Message):
                if reply:
                    return await msg.reply(text, **kwargs)
                else:
                    return await msg.edit(text, **kwargs)
            else:
                if reply:
                    return await msg.message.reply(text, **kwargs)
                else:
                    return await msg.message.edit_text(text, **kwargs)
        except Exception:
            pass

    async def ask(self, chat_id: int, text: str, *args, **kwargs):
        await self.send_message(chat_id, text, *args, **kwargs)
        loop = asyncio.get_running_loop()
        futr = loop.create_future()

        futr.add_done_callback(
            functools.partial(lambda _, uid: self.listening.pop(uid, None), chat_id)
        )
        self.listening[chat_id] = {"task": futr}

        try:
            return await asyncio.wait_for(futr, 60.0)
        except asyncio.TimeoutError:
            await self.send_message(chat_id, "⏳ Timeout: Process cancelled due to inactivity.")
            self.listening.pop(chat_id, None)
            return None

    async def use_listner(self, _, msg: Message):
        lstn = self.listening.get(msg.chat.id)
        if lstn and not lstn["task"].done():
            lstn["task"].set_result(msg)
        return msg.continue_propagation()

    async def full_cleanup(self, path: str = None, user_id: int = None):
        """Clean up tasks and files."""
        try:
            if user_id:
                self.glob_tmp.pop(user_id, None)
                self.clear_user_task(user_id)
                mg_pid = self.mega_running.pop(user_id, None)
                ddl_task = self.ddl_running.pop(user_id, None)
                if mg_pid:
                    await kill_family(mg_pid)
                if ddl_task and not ddl_task.done():
                    ddl_task.cancel()

            if path:
                await asyncio.to_thread(fs_cleanup, path)
        except Exception as e:
            logging.debug(f"Cleanup error: {e}")

    async def send_files(self, files: list[str], chat_id: int, msg_id: int, **kwargs):
        """Send files with auto-splitting and progress tracking."""
        if files:
            for file in files:
                if os.stat(file).st_size > self.mx_size:
                    await self.edit_message_text(
                        chat_id,
                        msg_id,
                        "🔪 **File exceeds 2GB! Splitting into smaller parts...**",
                    )
                    splout = f"{self.tmp_loc}/{chat_id}/splitted"
                    await splitit(file, splout, self.mx_size, self.splt_buffer)
                    for sfile in listfiles(splout):
                        await send_as_guessed(self, sfile, chat_id, msg_id, **kwargs)
                    fs_cleanup(splout)
                else:
                    await send_as_guessed(self, file, chat_id, msg_id, **kwargs)
        else:
            await self.edit_message_text(
                chat_id,
                msg_id,
                "⚠️ Could not find any files to upload.",
            )

    async def send_document(self, *args, **kwargs):
        try:
            return await super().send_document(*args, **kwargs)
        except errors.FloodWait as fw:
            await xsleep(fw.value)
            return await self.send_document(*args, **kwargs)

    async def send_video(self, *args, **kwargs):
        try:
            return await super().send_video(*args, **kwargs)
        except errors.FloodWait as fw:
            await xsleep(fw.value)
            return await self.send_video(*args, **kwargs)

    async def send_photo(self, *args, **kwargs):
        try:
            return await super().send_photo(*args, **kwargs)
        except errors.FloodWait as fw:
            await xsleep(fw.value)
            return await self.send_photo(*args, **kwargs)

    async def send_audio(self, *args, **kwargs):
        try:
            return await super().send_audio(*args, **kwargs)
        except errors.FloodWait as fw:
            await xsleep(fw.value)
            return await self.send_audio(*args, **kwargs)
