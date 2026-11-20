# Copyright (c) 2021 - Present partiallywritten
# Direct MEGA API Stream Downloader with On-the-Fly AES-CTR Decryption

import os
import time
import asyncio
import logging
from typing import Callable, Optional, Dict, Any
import aiohttp

from megadl.helpers.crypt import create_ctr_cipher

logger = logging.getLogger(__name__)


class MegaDownloader:
    """
    Downloads a single file from MEGA via the direct streaming API
    and decrypts it on-the-fly using AES-128 CTR mode.
    """

    API_URL = "https://g.api.mega.co.nz/cs"
    CHUNK_SIZE = 256 * 1024  # 256 KB chunk size for smooth progress & memory efficiency

    @classmethod
    async def download_node(
        cls,
        node: Dict[str, Any],
        dest_dir: str,
        progress_callback: Optional[Callable] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> str:
        """
        Download a file node from a public folder or public file link.
        """
        os.makedirs(dest_dir, exist_ok=True)
        file_name = node.get("n", "downloaded_file.bin")
        file_size = node.get("s", 0)
        k = node.get("k")
        iv = node.get("iv")
        node_handle = node.get("h")
        root_folder_id = node.get("root_folder_id")
        file_id = node.get("file_id")

        dest_path = os.path.join(dest_dir, file_name)

        # 1. Request direct download URL from MEGA API
        async with aiohttp.ClientSession() as session:
            if root_folder_id:
                # File inside a public shared folder
                params = {"id": int(time.time()), "n": root_folder_id}
                payload = [{"a": "g", "g": 1, "ssl": 2, "n": node_handle}]
            else:
                # Standalone public file
                params = {"id": int(time.time())}
                payload = [{"a": "g", "g": 1, "ssl": 2, "p": file_id or node_handle}]

            async with session.post(cls.API_URL, params=params, json=payload) as resp:
                data = await resp.json()

            if isinstance(data, list) and isinstance(data[0], int) and data[0] < 0:
                code = data[0]
                if code == -17:
                    raise RuntimeError("MEGA download quota exceeded! Please wait or use another IP.")
                elif code == -9:
                    raise FileNotFoundError("The requested file was not found on MEGA.")
                else:
                    raise RuntimeError(f"MEGA API error during download request: {code}")

            if not data or not isinstance(data, list) or "g" not in data[0]:
                raise RuntimeError("Failed to obtain direct download link from MEGA.")

            direct_url = data[0]["g"]
            actual_size = data[0].get("s", file_size)

            # 2. Setup AES-CTR Decryption Cipher
            cipher = create_ctr_cipher(k, iv)

            # 3. Stream download & decrypt to destination file
            start_time = time.time()
            last_edit_time = start_time
            downloaded = 0

            # Open local file in write-binary mode
            with open(dest_path, "wb") as outfile:
                async with session.get(direct_url) as stream_resp:
                    if stream_resp.status != 200:
                        raise RuntimeError(f"Download stream returned HTTP status {stream_resp.status}")

                    while True:
                        if cancel_check and cancel_check():
                            # User cancelled
                            outfile.close()
                            if os.path.exists(dest_path):
                                os.remove(dest_path)
                            raise asyncio.CancelledError("Download cancelled by user.")

                        chunk = await stream_resp.content.read(cls.CHUNK_SIZE)
                        if not chunk:
                            break

                        decrypted_chunk = cipher.decrypt(chunk)
                        outfile.write(decrypted_chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if progress_callback and (now - last_edit_time >= 3.0 or downloaded >= actual_size):
                            last_edit_time = now
                            diff = max(now - start_time, 0.001)
                            speed = downloaded / diff
                            eta = (actual_size - downloaded) / speed if speed > 0 else 0
                            try:
                                await progress_callback(
                                    downloaded=downloaded,
                                    total=actual_size,
                                    speed=speed,
                                    eta=eta,
                                    filename=file_name
                                )
                            except Exception as e:
                                logger.debug(f"Progress callback exception: {e}")

        return dest_path
