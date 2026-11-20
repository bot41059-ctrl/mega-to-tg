# Copyright (c) 2021 - Present partiallywritten
# Author: https://github.com/partiallywritten
# Project: https://github.com/partiallywritten/Mega.nz-Bot
# Description: Decryption functions with AES-CTR streaming support

import re
import json
import base64
import struct
import codecs
from Crypto.Cipher import AES
from Crypto.Util import Counter


def makebyte(x):
    return codecs.latin_1_encode(x)[0]


def makestring(x):
    return codecs.latin_1_decode(x)[0]


def aes_cbc_decrypt(data, key):
    aes_cipher = AES.new(key, AES.MODE_CBC, makebyte("\0" * 16))
    return aes_cipher.decrypt(data)


def str_to_a32(b):
    if isinstance(b, str):
        b = makebyte(b)
    if len(b) % 4:
        b += b"\0" * (4 - len(b) % 4)
    return struct.unpack(">%dI" % (len(b) / 4), b)


def base64_to_a32(s):
    return str_to_a32(base64_url_decode(s))


def a32_to_str(a):
    return struct.pack(">%dI" % len(a), *a)


def base64_url_decode(data):
    data += "=="[(2 - len(data) * 3) % 4 :]
    data = re.sub(r"[-_,]", lambda x: {"-": "+", "_": "/", ",": ""}[x.group()], data)
    return base64.b64decode(data)


def base64_url_encode(data):
    data = base64.b64encode(data).decode("ascii")
    data = re.sub(r"[+/=]", lambda x: {"+": "-", "/": "_", "=": ""}[x.group()], data)
    return data


def a32_to_base64(a):
    return base64_url_encode(a32_to_str(a))


def decrypt_attr(attr, key):
    try:
        attr = aes_cbc_decrypt(attr, a32_to_str(key))
        attr = makestring(attr)
        attr = attr.rstrip("\0")
        return json.loads(attr[4:]) if attr[:6] == 'MEGA{"' else False
    except Exception:
        return False


def aes_cbc_decrypt_a32(data, key):
    return str_to_a32(aes_cbc_decrypt(a32_to_str(data), a32_to_str(key)))


def decrypt_key(a, key):
    return sum(
        (aes_cbc_decrypt_a32(a[i : i + 4], key) for i in range(0, len(a), 4)), ()
    )


def decrypt_node_key(key_str: str, shared_key: tuple):
    if not key_str or ":" not in key_str:
        return None
    try:
        encrypted_key = base64_to_a32(key_str.split(":")[1])
        return decrypt_key(encrypted_key, shared_key)
    except Exception:
        return None


def create_ctr_cipher(k: tuple, iv: tuple, initial_block: int = 0):
    """
    Creates an AES-CTR cipher for streaming decryption of MEGA file data.
    """
    k_str = a32_to_str(k)
    initial_val = (((iv[0] << 32) + iv[1]) << 64) + initial_block
    counter = Counter.new(128, initial_value=initial_val)
    return AES.new(k_str, AES.MODE_CTR, counter=counter)
