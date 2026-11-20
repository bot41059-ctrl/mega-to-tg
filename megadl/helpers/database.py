# Copyright (c) 2021 - Present partiallywritten
# Author: https://github.com/partiallywritten
# Project: https://github.com/partiallywritten/Mega.nz-Bot
# Description: Safe Database wrapper with fallback

from os import getenv
import logging

try:
    from pymongo import AsyncMongoClient, ReturnDocument
except ImportError:
    try:
        from pymongo import MongoClient as AsyncMongoClient, ReturnDocument
    except ImportError:
        AsyncMongoClient = None
        ReturnDocument = None


class CypherDB:
    __slots__ = ("mongoc", "coll_users")

    def __init__(self) -> None:
        uri = getenv("MONGO_URI")
        if not uri or AsyncMongoClient is None:
            self.mongoc = None
            self.coll_users = None
        else:
            try:
                self.mongoc = AsyncMongoClient(uri)
                self.coll_users = self.mongoc["mega_nz"]["users"]
            except Exception as e:
                logging.warning(f"Failed to connect to MongoDB: {e}")
                self.mongoc = None
                self.coll_users = None

    async def add(self, user_id: int):
        if not self.coll_users:
            return {"banned": False, "reason": ""}
        try:
            result = await self.coll_users.find_one_and_update(
                {"_id": user_id},
                {
                    "$setOnInsert": {
                        "_id": user_id,
                        "email": "",
                        "password": "",
                        "status": {"banned": False, "reason": ""},
                        "total_downloads": 0,
                        "total_uploads": 0,
                        "proxy": "",
                    }
                },
                projection={"_id": 0, "status": 1},
                upsert=True,
                return_document=ReturnDocument.AFTER if ReturnDocument else None,
            )
            return result.get("status", {"banned": False, "reason": ""}) if result else {"banned": False, "reason": ""}
        except Exception:
            return {"banned": False, "reason": ""}

    async def plus_fl_count(
        self, user_id: int, downloads: int | None = None, uploads: int | None = None
    ):
        if not self.coll_users:
            return
        try:
            if downloads:
                await self.coll_users.update_one(
                    {"_id": user_id},
                    {"$inc": {"total_downloads": downloads}},
                )
            elif uploads:
                await self.coll_users.update_one(
                    {"_id": user_id},
                    {"$inc": {"total_uploads": uploads}},
                )
        except Exception:
            pass

    async def delete(self, user_id: int):
        if self.coll_users:
            try:
                await self.coll_users.delete_one({"_id": user_id})
            except Exception:
                pass

    async def is_there(self, user_id: int, use_acc: bool = False):
        if not self.coll_users:
            return None
        try:
            uid = {"_id": user_id}
            docu = await self.coll_users.find_one(uid, {"_id": 0})
            if not docu:
                return None
            if use_acc:
                return docu if not "" in (docu.get("email"), docu.get("password")) else None
            else:
                return docu
        except Exception:
            return None

    async def ban_user(self, user_id: int, reason: str = "Got banned :("):
        if self.coll_users:
            try:
                await self.coll_users.update_one(
                    {"_id": user_id},
                    {"$set": {"status": {"banned": True, "reason": reason}}},
                )
            except Exception:
                pass

    async def unban_user(self, user_id: int, reason: str = "Got unbanned :)"):
        if self.coll_users:
            try:
                await self.coll_users.update_one(
                    {"_id": user_id},
                    {"$set": {"status": {"banned": False, "reason": reason}}},
                )
            except Exception:
                pass

    async def mega_login(self, user_id: int, email: str, password: str):
        if self.coll_users:
            try:
                await self.coll_users.update_one(
                    {"_id": user_id},
                    {"$set": {"email": email, "password": password}},
                )
            except Exception:
                pass

    async def mega_logout(self, user_id: int):
        if self.coll_users:
            try:
                await self.coll_users.update_one(
                    {"_id": user_id},
                    {"$set": {"email": "", "password": ""}},
                )
            except Exception:
                pass

    async def update_proxy(self, user_id: int, proxy: str):
        if self.coll_users:
            try:
                await self.coll_users.update_one(
                    {"_id": user_id},
                    {"$set": {"proxy": proxy}},
                )
            except Exception:
                pass

    async def get_proxy(self, user_id: int):
        if self.coll_users:
            try:
                return await self.coll_users.find_one({"_id": user_id}, {"proxy": 1})
            except Exception:
                return None
        return None
