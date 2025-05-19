import json
import base64
import sqlite3
import shutil
from typing import Tuple, Any, Dict, Optional
from urllib.parse import urlparse
from pathlib import Path

from Cryptodome.Cipher import AES
import win32crypt

from utils.utils import code_logger


def decrypt_data(data: bytes) -> bytes:
    result: Tuple[Any, bytes] = win32crypt.CryptUnprotectData(data, None, None, None, 0)  # type: ignore
    return result[1]


def get_key() -> Optional[bytes]:
    try:
        code_logger.info("Getting enc key")
        profile = Path.home()
        local_state = profile / 'AppData' / 'Local' / 'BraveSoftware' / 'Brave-Browser' / 'User Data' / 'Local State'
        with local_state.open('r', encoding='utf-8') as f:
            state = json.load(f)

        enc_key_b64 = state['os_crypt']['encrypted_key']
        code_logger.info(f"Base64 key length: {len(enc_key_b64)}")

        decoded_key = base64.b64decode(enc_key_b64)
        code_logger.info(f"Decoded key length (including prefix): {len(decoded_key)}")

        prefix = decoded_key[:5]
        code_logger.info(f"Prefix: {prefix}")

        if prefix != b'DPAPI':
            code_logger.error("Encrypted key prefix is not 'DPAPI'. Key format may have changed or file corrupted.")
            return None

        enc_key = decoded_key[5:]
        code_logger.info(f"Decoded key (without prefix): {enc_key[:10]}... (total {len(enc_key)} bytes)")

        aes_key = decrypt_data(enc_key)
        code_logger.info(f"Decrypted AES key length: {len(aes_key)}")

        if len(aes_key) not in (16, 32):
            code_logger.warning(f"Decrypted AES key length unusual: {len(aes_key)} bytes")

        return aes_key

    except Exception as e:
        code_logger.error(f"An error has occurred while trying to get the enc key from {e}", exc_info=True)
        return None


def decrypt_cookie(enc_value: bytes, key: bytes) -> str:
    if enc_value[:3] == b'v10':
        iv = enc_value[3:15]
        payload = enc_value[15:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)  # type: ignore
        ciphertext = payload[:-16]
        tag = payload[-16:]
        decrypted = cipher.decrypt_and_verify(ciphertext, tag)
        return decrypted.decode()
    else:
        if len(enc_value) == 0:
            return ''
        try:
            return win32crypt.CryptUnprotectData(enc_value, None, None, None, 0)[1].decode()  # type: ignore
        except Exception as e:
            code_logger.error(f"DPAPI fallback decrypt failed: {e}")
            return ''


def extract_cookies(url: str) -> Dict[str, str]:
    code_logger.info("Extracting cookies")
    domain = urlparse(url).hostname
    if not domain:
        raise ValueError("Invalid URL.")

    key = get_key()
    cookies_path = Path("data/config/Cookies")
    db_copy = cookies_path.with_suffix('.copy')
    shutil.copy2(cookies_path, db_copy)

    conn = sqlite3.connect(db_copy)
    cursor = conn.cursor()

    sql = """
    SELECT host_key, path, name, encrypted_value, expires_utc
    FROM cookies
    WHERE host_key LIKE ? OR host_key LIKE ?
    """
    like_patterns = (f'%{domain}', f'.{domain}')
    cursor.execute(sql, like_patterns)

    cookies: Dict[str, str] = {}
    for host_key, _, name, encrypted_value, _ in cursor.fetchall():
        try:
            if key is None:
                raise ValueError("Key cannot be None")

            decrypted_value = decrypt_cookie(encrypted_value, key)
            if decrypted_value:  # skip empty strings
                cookies[name] = decrypted_value

        except Exception as e:
            code_logger.error(f"Failed to extract cookies: {e}")
            continue

    conn.close()
    db_copy.unlink(missing_ok=True)
    code_logger.info(f"Cookies: {cookies}")
    return cookies
