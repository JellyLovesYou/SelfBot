import asyncio
import atexit
import ctypes
import difflib
import json
import os
import pathlib
import re
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import List, Optional, cast

import aiohttp
import discord
from discord import Message, Embed
from discord.ext import commands
from dotenv import load_dotenv
import pytesseract  # type: ignore
from PIL import Image

from utils.data import p2verification_message
from utils.grow_a_tree import create_tree_watcher
from utils.telecom import text
from utils.utils import (
    clean_logs,
    code_logger,
    discord_logger,
    pokemon_logger,
    fish_logger,
    env,
    prefix,
)
from utils.virtual_fisher import (
    create_emphemeral_watcher,
    send_verify_code,
    start_browser,
    fish,
    sell,
)


config_path = Path("data/config/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)

with open(config_path) as f:
    config = json.load(f)

venv = str(config['paths']['venv'])
load_dotenv(dotenv_path=Path(env))
token = os.getenv('discord_token')

guild_id = int(config['ids']['guild'])
bot_version = str(config['main']['version'])
username = str(config['main']['username'])
nickname = str(config['main']['nickname'])
catching_check = bool(config['main']['catching?'])
p2assistant_check = bool(config['main']['p2assistant?'])
helpers_check = bool(config['main']['helpers?'])
solving_check = bool(config['main']['solving?'])
sniping_check = bool(config['main']['sniping?'])

fishing_check = bool(config['main']['fishing?'])
if fishing_check:
    fishing_paid = bool(config['main']['fishing paid?'])
    fish_watch_id = int(config['ids']['fish id'])
    fishing_channel = int(config['ids']['fish channel'])
    fishing_text_check = bool(config['text']['fishing'])
    fishing_url = str(f"https://discord.com/channels/{guild_id}/{fishing_channel}")

user_id = int(config['main']['user id'])
if catching_check:
    watch_id = int(config['ids']['watch id'])
    mention_id = int(config['ids']['mention id'])
    pokemon_text_check = bool(config['text']['pokemon'])

tree_check = bool(config['main']['tree?'])
if tree_check:
    tree_message_id = int(config['ids']['tree'])
    tree_channel_id = int(config['ids']['tree channel'])

helpers = "helpers.py"
restart = "data/runtime/restart.signal"
pokemon = "data/text/pokemon.txt"
session = "data/text/session.txt"

Lego = commands.Bot(command_prefix=prefix, self_bot=True)
last_help_time = 0
cooldown_lock = asyncio.Lock()
MAX_RETRIES = 1
current_pokemon = None
pokemon_data = {}
catching = True
already_triggered = False
tree_monitor_task = None
fishing_loop_check = None
fishing_clear = True
helper_proc = None

with open(pokemon, "r", encoding='utf-8') as f:
    pokemon_list = [line.strip() for line in f if line.strip()]


if pathlib.Path(restart).exists():
    pathlib.Path(restart).unlink()


def get_help():
    global helper_proc
    if not os.path.exists(venv):
        code_logger.error(f"Error: The virtual environment Python executable does not exist at {venv}", exc_info=True)
    elif not os.path.exists(helpers):
        code_logger.error(f"Error: The helpers.py file does not exist at {helpers}", exc_info=True)
    else:
        helper_proc = subprocess.Popen([venv, helpers])


def is_structure_match(hint: str, candidate: str) -> bool:
    if len(hint) != len(candidate):
        return False
    for h_char, c_char in zip(hint, candidate):
        if h_char != '_' and h_char != c_char:
            return False
    return True


def normalize(s: str, keep_structure: bool = False) -> str:
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(
        c for c in s
        if unicodedata.category(c).startswith('L') or (keep_structure and c in {'-', '_'})
    )
    return s


def get_closest_pokemon(hint: str, pokemon_list: List[str]) -> Optional[str]:
    try:
        hint_raw = hint.lower().replace("the pokémon is", "").strip(" .").strip()
        normalized_hint = normalize(hint_raw, keep_structure=True)

        def structure_match(hint: str, name: str) -> bool:
            if len(hint) != len(name):
                return False
            return all(h == n or h == '_' for h, n in zip(hint, name))

        filtered = [
            p for p in pokemon_list
            if structure_match(normalized_hint, normalize(p, keep_structure=True))
        ]

        if not filtered:
            return None

        cleaned_names = [normalize(p) for p in filtered]
        best_match = difflib.get_close_matches(normalize(hint_raw).replace('_', ''), cleaned_names, n=1)

        if best_match:
            for p in filtered:
                if normalize(p) == best_match[0]:
                    return p
        return None

    except Exception as e:
        code_logger.error(f"An exception occurred while trying to get closest pokemon name {e}", exc_info=True)
        return None


def extract_embed_text(embed: Embed) -> str:
    parts: List[str] = []

    if hasattr(embed, "author") and embed.author and getattr(embed.author, "name", None):
        parts.append(str(embed.author.name))
    if embed.title:
        parts.append(str(embed.title))
    if embed.description:
        parts.append(str(embed.description))
    if embed.fields:
        parts.extend([str(f.name) + str(f.value) for f in embed.fields])
    if embed.footer and embed.footer.text:
        parts.append(str(embed.footer.text))

    return ' '.join(parts)


def extract_captcha_code(msg: str) -> Optional[str]:
    code_block = re.search(r"```(.*?)```", msg, re.DOTALL)
    if code_block:
        inside = code_block.group(1)
        match = re.search(r"Code:\s*([a-zA-Z0-9]+)", inside)
        if match:
            return match.group(1)
    return None


async def fishing_loop():
    global fishing_check, fishing_clear
    if fishing_check:
        fish_logger.info("Fish monitor loop started")
        await start_browser(fishing_url)
        await create_emphemeral_watcher()
        while fishing_clear:
            try:
                fish_logger.info("Fish called")
                await fish()
                if fishing_paid is not True:
                    fish_logger.info("Selling fish")
                    await sell()
                    fish_logger.info("Fish sold")
                await asyncio.sleep(4.3)
                fish_logger.info("waiting 4s")
            except asyncio.CancelledError:
                fish_logger.info("Fishing fish loop cancelled.")


@Lego.event
async def on_ready():
    global fishing_check, fishing_clear, fishing_loop_check

    try:
        discord_logger.info("Main Selfbot has started.")
        loaded_cogs: list[str] = []
        for root, _, files in os.walk('./cogs'):
            for filename in files:
                if filename.endswith('.py'):
                    cog_path = os.path.join(root, filename)
                    cog_module = cog_path.replace(os.sep, '.')[2:-3]
                    try:
                        await Lego.load_extension(cog_module)
                        loaded_cogs.append(cog_module)
                    except Exception as e:
                        code_logger.error(f"Failed to load extension {cog_module}: {e}", exc_info=True)

        missing_cogs: list[str] = []
        for root, _, files in os.walk('./cogs'):
            for filename in files:
                if filename.endswith('.py'):
                    cog_module = os.path.join(root, filename).replace(os.sep, '.')[2:-3]
                    if cog_module not in loaded_cogs:
                        missing_cogs.append(cog_module)

        if missing_cogs:
            code_logger.warning(f"The following cogs are missing! {missing_cogs}.")

    except Exception as e:
        code_logger.error(f"An error occurred during bot startup: {e}", exc_info=True)

    try:
        session_id = Lego.ws.session_id
        with open(session, "w") as f:
            f.write(str(session_id))
    except Exception as e:
        code_logger.error(f"An error has occured while trying to update {session}, {e}", exc_info=True)

    try:
        if tree_check:
            asyncio.create_task(create_tree_watcher())

        if fishing_check and fishing_clear:
            if fishing_loop_check is None or fishing_loop_check.done():
                fishing_loop_check = asyncio.create_task(fishing_loop())
                fish_logger.info("Fish monitor loop task created")
            else:
                fish_logger.info("Fish monitor loop already running")
        else:
            if fishing_loop_check and not fishing_loop_check.done():
                fishing_loop_check.cancel()
                fish_logger.info("Fish monitor loop task cancelled")

    except Exception as e:
        code_logger.error(f"There was an error trying to monitor the tree, {e}", exc_info=True)


@Lego.event
async def on_message(message: discord.Message):
    global catching, last_help_time, already_triggered, fishing_clear

    # PokeTwo
    if catching_check and catching:
        if message.author.id == mention_id:
            if message.embeds:
                for embed in message.embeds:
                    embed_content = str(embed.title or "") + str(embed.description or "")
                    if "pokémon has appeared!" in embed_content or "That is the wrong pokémon!" in embed_content:

                        if cooldown_lock.locked():
                            pokemon_logger.info("Cooldown lock active. Skipping.")
                            continue

                        async with cooldown_lock:
                            pokemon_logger.info(f"{embed.title}")
                            now = time.time()
                            time_since_last = now - last_help_time

                            if time_since_last < 10:
                                wait_time = 10 - time_since_last
                                pokemon_logger.info(f"Rate limit hit. Waiting {wait_time:.2f}s.")
                                await asyncio.sleep(wait_time)

                            try:
                                help_msg = await message.channel.send(f"<@{mention_id}> h")
                                last_help_time = time.time()
                                help_msg_time = help_msg.created_at

                                def response_check(m: Message) -> bool:
                                    return (
                                        m.author.id == mention_id and m.channel.id == message.channel.id and m.created_at > help_msg_time
                                    )  # type: ignore

                                try:
                                    await Lego.wait_for("message", timeout=5.0, check=response_check)
                                    pokemon_logger.info("Pokétwo responded to first h, no retry needed.")
                                except asyncio.TimeoutError:
                                    pokemon_logger.warning("No response to first h. Waiting and retrying once.")

                                    retry_delay = 10 - (time.time() - last_help_time)
                                    if retry_delay > 0:
                                        await asyncio.sleep(retry_delay)

                                    try:
                                        await message.channel.send(f"<@{mention_id}> h")
                                        last_help_time = time.time()
                                    except Exception as e:
                                        code_logger.error(f"Retry send failed: {e}", exc_info=True)

                            except Exception as e:
                                code_logger.error(f"Failed to send or retry help: {e}", exc_info=True)

            if "Whoa there. Please tell us you're human!" in message.content:
                try:
                    catching = False
                    pokemon_logger.info(f"catching_check type: {type(catching_check)}, value: {repr(catching_check)}")
                    pokemon_logger.info(f'{p2verification_message}')
                    assert isinstance(catching_check, bool), f"Expected boolean, got {type(catching_check)}: {repr(catching_check)}"

                    if not already_triggered:
                        pokemon_logger.info(f"{catching_check} and not {already_triggered} check success.")
                        try:
                            if pokemon_text_check:
                                await text(p2verification_message)
                                pokemon_logger.info("A text was sent")
                                already_triggered = True

                        except Exception as e:
                            code_logger.error(f'Failed to send verification text: {e}', exc_info=True)

                except Exception as e:
                    code_logger.error(f'Unhandled error during CAPTCHA flow: {e}', exc_info=True)

            elif "Congratulations" in message.content:
                try:
                    cleaned = re.sub(r"<@!?[0-9]+>", "", message.content)
                    cleaned = re.sub(r"<:.*?:\d+>", "", cleaned)
                    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
                    pokemon_logger.info(f"{cleaned}")
                except Exception as e:
                    code_logger.error(f"An Exception has occurred logging a catch {e}", exc_info=True)

            elif message.content.startswith('The pokémon is') or p2assistant_check:
                if message.author.id == watch_id:
                    try:
                        guild_name = message.guild.name if message.guild else "Direct Message"
                        pokemon_logger.info(f"Message from watch_id detected: {message.content} in {guild_name}")
                        match = re.match(r'(.+?):\s*\d+(.\d+)?%', message.content)
                        if match:
                            name = match.group(1)
                            if not any(name.lower() == p.lower() for p in pokemon_list):
                                pokemon_logger.info(f"Unmatched Pokémon (exact mode): '{name}' from message: '{message.content}'")

                            response = f'<@{mention_id}> c {name}'
                            pokemon_logger.info(f"Parsed name: {name}, sending response: {response}")
                            try:
                                await message.channel.send(response)
                            except discord.NotFound:
                                pokemon_logger.error(f"Message or channel not found. Possibly deleted: {message.id}")
                        else:
                            pokemon_logger.warning("No match found in the message content")
                    except KeyError as e:
                        code_logger.error(f'KeyError for {e} in message: {message.content}', exc_info=True)
                else:
                    try:
                        pokemon_logger.info(f"Parsing pokemon name from help. {message.content}")
                        closest_name = get_closest_pokemon(message.content, pokemon_list)

                        if closest_name:
                            await message.channel.send(f"<@{mention_id}> c {closest_name}")

                        if not closest_name:
                            pokemon_logger.info(f"Unmatched Pokémon (fuzzy mode): '{message.content}'")

                    except Exception as e:
                        code_logger.error(f"Failed to find closest Pokémon in '{message.content}': {e}")

        if p2assistant_check:
            if message.author.id == watch_id:
                try:
                    guild_name = message.guild.name if message.guild else "Direct Message"
                    pokemon_logger.info(f"Message from watch_id detected: {message.content} in {guild_name}")
                    match = re.match(r'(.+?):\s*\d+(.\d+)?%', message.content)
                    if match:
                        name = match.group(1)
                        response = f'<@{mention_id}> c {name}'
                        pokemon_logger.info(f"Parsed name: {name}, sending response: {response}")
                        try:
                            await message.channel.send(response)
                        except discord.NotFound:
                            pokemon_logger.error(f"Message or channel not found. Possibly deleted: {message.id}")
                    else:
                        pokemon_logger.warning("No match found in the message content")
                except KeyError as e:
                    code_logger.error(f'KeyError for {e} in message: {message.content}', exc_info=True)

    # Virtual Fisher
    if fishing_check:
        if message.author.id == fish_watch_id:
            if message.embeds:
                for embed in message.embeds:
                    embed_content = extract_embed_text(embed)
                    if username in embed_content:
                        if "Anti-bot" in embed_content:
                            try:
                                fish_logger.warning("Fisher is asking for verification")

                                fishing_clear = False

                                if fishing_loop_check:
                                    fishing_loop_check.cancel()
                                    fish_logger.info("Fish monitor loop task cancelled")

                                if fishing_text_check:
                                    await text("Virtual Fisher is asking for verification")
                                    fish_logger.info("A text was sent")

                                if solving_check:
                                    for embed in message.embeds:
                                        if embed.image and embed.image.url:
                                            image_url = embed.image.url
                                            file_name = os.path.basename(image_url).split("?")[0]
                                            save_path = os.path.join("data", "captchas", file_name)

                                            os.makedirs(os.path.dirname(save_path), exist_ok=True)

                                            async with aiohttp.ClientSession() as session:
                                                async with session.get(image_url) as resp:
                                                    if resp.status == 200:
                                                        with open(save_path, "wb") as f:
                                                            f.write(await resp.read())
                                                        fish_logger.info(f"Captcha image saved to {save_path}")

                                                        try:
                                                            img = Image.open(save_path)
                                                            raw_result = pytesseract.image_to_string(img, config='--psm 8')  # type: ignore
                                                            code: str = cast(str, raw_result).strip() if raw_result else ""

                                                            fish_logger.info(f"Extracted verification code: {code}")

                                                            if code:
                                                                await send_verify_code(code)
                                                            else:
                                                                fish_logger.warning("OCR failed to extract a code.")
                                                        except Exception as e:
                                                            fish_logger.error(f"OCR error: {e}")
                                                    else:
                                                        fish_logger.warning(f"Failed to download captcha image: HTTP {resp.status}")

                                if "code:" in embed_content.lower():
                                    code: str = extract_captcha_code(embed_content) or ""
                                    if code:
                                        fish_logger.warning(f"[CAPTCHA] Detected code: sending /verify {code}")
                                        await send_verify_code(code)
                                        fishing_clear = True

                            except Exception as e:
                                code_logger.error(f"An exception occurred while appending fishing.txt, {e}", exc_info=True)

                    elif nickname in embed_content:
                        if "solve the captcha" in embed_content:
                            try:
                                fishing_clear = False
                                fish_logger.warning("Fisher is asking for verification, stop fishing.")

                                if fishing_text_check:
                                    await text("Virtual Fisher has already asked for verification, stop fishing.")

                            except Exception as e:
                                code_logger.error(f"An error has occurred, {e}", exc_info=True)

                        if "You caught:" in embed_content:
                            try:
                                fish_logger.debug(f"Raw embed content: {repr(embed_content)}")

                                xp_match = re.search(r'\+(\d{1,3}(?:,\d{3})*) XP', embed_content)
                                xp = xp_match.group(1).replace(',', '') if xp_match else "0"

                                if fishing_paid:
                                    payment_match = re.search(r'sold them for \$(\d+,?\d*)', embed_content)
                                    payment = payment_match.group(1).replace(',', '') if payment_match else "0"

                                    balance_match = re.search(r'now have \$(\d+,?\d*)', embed_content)
                                    balance = balance_match.group(1).replace(',', '') if balance_match else "0"

                                    fish_logger.info(f"you made ${payment}, and gained {xp} XP this catch, you now have ${balance}")
                                else:
                                    fish_logger.info(f"you gained {xp} XP this catch.")
                            except Exception as e:
                                fish_logger.error(f"Failed to parse catch results: {e}")

                            if "LEVEL UP" in embed_content:
                                try:
                                    level_match = re.search(r"You are now level (\d+)", embed_content)
                                    if level_match:
                                        level = int(level_match.group(1))
                                        fish_logger.info(f"[LEVEL UP] You have leveled up to level {level}!")
                                    else:
                                        fish_logger.warning("LEVEL UP detected but could not extract level number.")
                                except Exception as e:
                                    code_logger.error(f"Error parsing level up message: {e}", exc_info=True)

    # Mentions
    if Lego.user in message.mentions:
        discord_logger.info(f"Message from {message.author}: {message.content}")

    await Lego.process_commands(message)


@atexit.register
def cleanup():
    if helper_proc and helper_proc.poll() is None:
        helper_proc.terminate()


if __name__ == "__main__":
    clean_logs()
    if helpers_check:
        get_help()
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
    if token is None:
        raise ValueError("TOKEN environment variable is missing.")
    Lego.run(token)
