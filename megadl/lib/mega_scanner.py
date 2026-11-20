# Copyright (c) 2021 - Present partiallywritten
# Enhanced for Recursive Folder & Video Scanning

import re
import json
import logging
from typing import Dict, List, Any, Optional
import aiohttp

from megadl.helpers.crypt import (
    base64_to_a32,
    decrypt_node_key,
    decrypt_attr,
    base64_url_decode,
)

logger = logging.getLogger(__name__)

# Standard video file extensions
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv",
    ".webm", ".ts", ".m4v", ".3gp", ".rmvb", ".mpeg",
    ".mpg", ".vob", ".m2ts", ".ogv"
}


def format_size(b: int) -> str:
    """Format bytes into human-readable string."""
    val = float(b)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024:
            return f"{val:.2f} {unit}"
        val /= 1024
    return f"{val:.2f} PB"


class MegaUrlParser:
    folder_regex = re.compile(
        r"mega\.[^/]+/(?:folder/([0-9a-zA-Z_-]+)#|(?:(?:#F!([0-9a-zA-Z_-]+))[!#]))([0-9a-zA-Z_-]+)"
    )
    file_regex = re.compile(
        r"mega\.[^/]+/(?:file/([0-9a-zA-Z_-]+)#|#!([0-9a-zA-Z_-]+)!)([0-9a-zA-Z_-]+)"
    )

    @classmethod
    def parse(cls, url: str):
        folder_match = cls.folder_regex.search(url)
        if folder_match:
            groups = [g for g in folder_match.groups() if g is not None]
            return {"type": "folder", "id": groups[0], "key": groups[1]}

        file_match = cls.file_regex.search(url)
        if file_match:
            groups = [g for g in file_match.groups() if g is not None]
            return {"type": "file", "id": groups[0], "key": groups[1]}

        return None


class MegaScanner:
    """
    Scans MEGA public folders recursively:
    - Traverses all folders & subfolders
    - Decrypts all node metadata (names, sizes, types)
    - Filters and lists all video files
    - Produces a visual tree representation and scan statistics
    """

    API_URL = "https://g.api.mega.co.nz/cs"

    @classmethod
    async def scan(cls, url: str) -> Dict[str, Any]:
        parsed = MegaUrlParser.parse(url)
        if not parsed:
            raise ValueError("Invalid MEGA link. Supported: mega.nz/folder/... or mega.nz/file/...")

        if parsed["type"] == "file":
            return await cls._scan_file(parsed["id"], parsed["key"], url)
        else:
            return await cls._scan_folder(parsed["id"], parsed["key"], url)

    @classmethod
    async def _scan_file(cls, file_id: str, file_key: str, original_url: str) -> Dict[str, Any]:
        """Fetch metadata for a single public file."""
        async with aiohttp.ClientSession() as session:
            payload = [{"a": "g", "ad": 1, "p": file_id}]
            async with session.post(cls.API_URL, json=payload) as resp:
                data = await resp.json()

        if isinstance(data, list) and isinstance(data[0], int) and data[0] < 0:
            error_code = data[0]
            if error_code == -9:
                raise ValueError("File does not exist or has been deleted.")
            elif error_code == -11:
                raise ValueError("Access denied to this file.")
            elif error_code == -16:
                raise ValueError("File has been blocked due to Terms of Service violation.")
            else:
                raise ValueError(f"MEGA API error code: {error_code}")

        file_data = data[0]
        key = base64_to_a32(file_key)
        tk = (key[0] ^ key[4], key[1] ^ key[5], key[2] ^ key[6], key[3] ^ key[7])
        fsize = file_data.get("s", 0)
        attrs = decrypt_attr(base64_url_decode(file_data["at"]), tk)
        fname = attrs.get("n", "Unknown_File") if attrs else "Unknown_File"

        ext = ("." + fname.split(".")[-1].lower()) if "." in fname else ""
        is_video = ext in VIDEO_EXTENSIONS

        return {
            "is_folder": False,
            "url": original_url,
            "file_id": file_id,
            "file_key": file_key,
            "name": fname,
            "size": fsize,
            "size_str": format_size(fsize),
            "is_video": is_video,
            "key_tuple": key,
            "k_tuple": tk,
            "iv": key[4:6] + (0, 0),
        }

    @classmethod
    async def _scan_folder(cls, root_folder_id: str, shared_enc_key: str, original_url: str) -> Dict[str, Any]:
        """Fetch all nodes in a public folder, decrypt attributes, and build tree."""
        shared_key = base64_to_a32(shared_enc_key)

        async with aiohttp.ClientSession() as session:
            payload = [{"a": "f", "c": 1, "ca": 1, "r": 1}]
            params = {"id": 0, "n": root_folder_id}
            async with session.post(cls.API_URL, params=params, json=payload) as resp:
                data = await resp.json()

        if isinstance(data, list) and isinstance(data[0], int) and data[0] < 0:
            error_code = data[0]
            if error_code == -9:
                raise ValueError("Folder does not exist or has been deleted.")
            elif error_code == -11:
                raise ValueError("Access denied to this folder.")
            elif error_code == -16:
                raise ValueError("Folder is blocked due to Terms of Service violation.")
            else:
                raise ValueError(f"MEGA API error: code {error_code}")

        if not data or not isinstance(data, list) or "f" not in data[0]:
            raise ValueError("No files found or empty folder.")

        raw_nodes = data[0]["f"]
        nodes_by_id: Dict[str, Dict[str, Any]] = {}
        children_map: Dict[str, List[Dict[str, Any]]] = {}

        # 1. Decrypt each node
        for node in raw_nodes:
            handle = node.get("h")
            parent = node.get("p", "")
            node_type = node.get("t", 0)  # 0: file, 1: folder
            key_str = node.get("k")
            attr_str = node.get("a")

            if not key_str or not attr_str:
                continue

            node_key = decrypt_node_key(key_str, shared_key)
            if not node_key:
                continue

            if node_type == 1:
                # Folder
                attrs = decrypt_attr(base64_url_decode(attr_str), node_key)
                name = attrs.get("n", f"Folder_{handle}") if attrs else f"Folder_{handle}"
                node_dict = {
                    "h": handle,
                    "p": parent,
                    "t": 1,
                    "n": name,
                    "key": node_key,
                }
            else:
                # File
                k = (
                    node_key[0] ^ node_key[4],
                    node_key[1] ^ node_key[5],
                    node_key[2] ^ node_key[6],
                    node_key[3] ^ node_key[7],
                )
                attrs = decrypt_attr(base64_url_decode(attr_str), k)
                name = attrs.get("n", f"File_{handle}") if attrs else f"File_{handle}"
                size = node.get("s", 0)
                iv = node_key[4:6] + (0, 0)
                node_dict = {
                    "h": handle,
                    "p": parent,
                    "t": 0,
                    "n": name,
                    "s": size,
                    "key": node_key,
                    "k": k,
                    "iv": iv,
                }

            nodes_by_id[handle] = node_dict
            children_map.setdefault(parent, []).append(node_dict)

        # 2. Determine root folder name
        # Root node usually has parent that is not in nodes_by_id or empty parent
        root_nodes = [
            n for n in nodes_by_id.values()
            if n["t"] == 1 and (not n["p"] or n["p"] not in nodes_by_id)
        ]
        root_name = root_nodes[0]["n"] if root_nodes else "MEGA Folder"
        root_handle = root_nodes[0]["h"] if root_nodes else ""

        # 3. Path calculation function
        def get_relative_path(nid: str) -> str:
            parts = []
            curr = nodes_by_id.get(nid)
            while curr:
                parts.append(curr["n"])
                curr = nodes_by_id.get(curr.get("p"))
            return " / ".join(reversed(parts))

        # 4. Filter video files and others
        video_files = []
        other_files = []
        total_folders = sum(1 for n in nodes_by_id.values() if n["t"] == 1 and n["h"] != root_handle)

        for n in nodes_by_id.values():
            if n["t"] == 0:
                name = n["n"]
                ext = ("." + name.split(".")[-1].lower()) if "." in name else ""
                n["ext"] = ext
                n["rel_path"] = get_relative_path(n["h"])
                n["size_str"] = format_size(n.get("s", 0))
                n["root_folder_id"] = root_folder_id

                if ext in VIDEO_EXTENSIONS:
                    video_files.append(n)
                else:
                    other_files.append(n)

        # Sort videos by relative path / name
        video_files.sort(key=lambda x: x["rel_path"])
        total_video_size = sum(v.get("s", 0) for v in video_files)
        total_all_size = total_video_size + sum(o.get("s", 0) for o in other_files)

        # 5. Build visual tree structure
        def render_tree(nid: str, prefix: str = "", depth: int = 0) -> List[str]:
            lines = []
            ch = children_map.get(nid, [])
            folders = [x for x in ch if x["t"] == 1]
            files = [x for x in ch if x["t"] == 0]
            items = folders + files

            # To prevent excessively large messages, summarize folders if depth > 3 or many items
            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "
                item_name = item["n"]

                if item["t"] == 1:
                    # Folder
                    def count_vids(sub_id: str) -> int:
                        cnt = 0
                        for c in children_map.get(sub_id, []):
                            if c["t"] == 0 and ("." + c["n"].split(".")[-1].lower() in VIDEO_EXTENSIONS):
                                cnt += 1
                            elif c["t"] == 1:
                                cnt += count_vids(c["h"])
                        return cnt

                    v_cnt = count_vids(item["h"])
                    lines.append(f"{prefix}{connector}📁 {item_name} ({v_cnt} videos)")
                    if depth < 3:
                        lines.extend(render_tree(item["h"], prefix + sub_prefix, depth + 1))
                else:
                    # File
                    ext = "." + item_name.split(".")[-1].lower() if "." in item_name else ""
                    if ext in VIDEO_EXTENSIONS:
                        icon = "🎬"
                        lines.append(f"{prefix}{connector}{icon} {item_name} ({format_size(item.get('s', 0))})")
                    else:
                        icon = "📄"
                        # Only show non-video files if fewer than 20 items in folder
                        if len(items) <= 15:
                            lines.append(f"{prefix}{connector}{icon} {item_name} ({format_size(item.get('s', 0))})")

            return lines

        tree_lines = [f"📁 {root_name}"]
        if root_handle:
            tree_lines.extend(render_tree(root_handle))
        else:
            # Fallback for flat or disjoint nodes
            for r in root_nodes:
                tree_lines.extend(render_tree(r["h"]))

        tree_text = "\n".join(tree_lines)
        if len(tree_text) > 2500:
            tree_text = tree_text[:2400] + "\n... [Tree truncated due to Telegram size limit]"

        return {
            "is_folder": True,
            "url": original_url,
            "root_id": root_folder_id,
            "root_name": root_name,
            "total_folders": total_folders,
            "total_videos": len(video_files),
            "total_other": len(other_files),
            "total_video_size": total_video_size,
            "total_video_size_str": format_size(total_video_size),
            "total_all_size": total_all_size,
            "total_all_size_str": format_size(total_all_size),
            "tree_text": tree_text,
            "videos": video_files,
            "other_files": other_files,
            "shared_key": shared_key,
        }
