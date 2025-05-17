import asyncio
import ctypes
import difflib
import json
import os
import pathlib
import re
import subprocess
import time
from pathlib import Path
from typing import Any, List, Optional

import discord
from discord import Message
from discord.ext import commands
from dotenv import load_dotenv

from utils.telecom import text
from utils.data import p2verification
from utils.utils import clean_logs, load_activity, save_activity, code_logger, discord_logger, pokemon_logger, env, prefix


config_path = Path("data/config/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)


with open(config_path) as f:
    config = json.load(f)

bot_version = config['main']['version']
watch_id = int(config['ids']['watch id'])
mention_id = int(config['ids']['mention id'])
catching_check = config['main']['catching?']
p2assistant_check = config['main']['p2assistant?']
texting_check = config['main']['texts?']
helpers_check = config['main']['helpers?']
tree_channel_id = int(config['ids']['tree'])
pokemon_check = config['text']['pokemon']
helpers = config['paths']['helpers']
restart = config['paths']['restart']
pokemon = config['paths']['pokemon']
venv = config['paths']['venv']
Lego = commands.Bot(command_prefix=prefix, self_bot=True)


load_dotenv(dotenv_path=Path(env))
token = os.getenv('discord_token')
last_help_time = 0
cooldown_lock = asyncio.Lock()
MAX_RETRIES = 1
current_pokemon = None
pokemon_data = {}
catching = True
already_triggered = False


with open(pokemon, "r", encoding='utf-8') as f:
    pokemon_list = json.load(f)


if pathlib.Path(restart).exists():
    pathlib.Path(restart).unlink()


def stop_sending():
    activity_data = load_activity()

    if activity_data and activity_data.get("sending", {}).get("active"):
        activity_data['sending']['active'] = False
        save_activity(activity_data)
        pokemon_logger.info("Stopped 'sending' activity.")


def get_help():
    if not os.path.exists(venv):
        code_logger.error(f"Error: The virtual environment Python executable does not exist at {venv}", exc_info=True)
    elif not os.path.exists(helpers):
        code_logger.error(f"Error: The helpers.py file does not exist at {helpers}", exc_info=True)
    else:
        subprocess.Popen([venv, helpers])


def is_structure_match(hint: str, candidate: str) -> bool:
    if len(hint) != len(candidate):
        return False
    for h_char, c_char in zip(hint, candidate):
        if h_char != '_' and h_char != c_char:
            return False
    return True


def get_closest_pokemon(hint: str, pokemon_list: List[str]) -> Optional[str]:
    try:
        hint_raw = hint.lower().replace("the pokémon is", "").strip(" .").strip()
        normalized_hint = re.sub(r'[^a-z_]', '', hint_raw)

        filtered: List[str] = [
            p for p in pokemon_list
            if is_structure_match(normalized_hint, re.sub(r'[^a-z]', '', p.lower()))
        ]

        if not filtered:
            return None

        cleaned_names = [re.sub(r'[^a-z]', '', p.lower()) for p in filtered]
        best_match = difflib.get_close_matches(normalized_hint.replace('_', ''), cleaned_names, n=1)

        if best_match:
            for p in filtered:
                if re.sub(r'[^a-z]', '', p.lower()) == best_match[0]:
                    return p
        return None
    except Exception as e:
        code_logger.error(f"An exception occurred while trying to get closest pokemon name {e}", exc_info=True)
        return None


@Lego.event
async def on_message(message: discord.Message):
    global catching
    global last_help_time
    global already_triggered
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
                                    )

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
                    pokemon_logger.warning(f'{p2verification}')

                    if pokemon_check and not already_triggered:
                        try:
                            if texting_check:
                                text(p2verification)
                            discord_logger.info("A text was sent")
                            stop_sending()
                            already_triggered = True
                        except Exception as e:
                            discord_logger.error(f'Failed to send verification text: {e}', exc_info=True)

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

    if message.channel.id == tree_channel_id:
        if message.embeds and message.components:
            for embed in message.embeds:
                embed_content = embed.description or ""

                if "Last watered by:" in embed_content and "Ready to be watered!" in embed_content:
                    discord_logger.info("Tree is ready to be watered!")
                    last_watered_match = re.search(r"Last watered by: @(\w+)", embed_content)

                    if last_watered_match:
                        last_watered_by = last_watered_match.group(1)

                        if (last_watered_by.lower() != (Lego.user.name.lower() if Lego.user else "") and "Ready to be watered!" in embed_content):
                            for row in message.components:
                                component = Any
                                for component in row.children:  # type: ignore[reportUnknownMemberType]
                                    if component.type == discord.ComponentType.button:  # type: ignore[reportUnknownMemberType]
                                        if "💧" in str(component.emoji) or component == row.children[0]:  # type: ignore[reportUnknownMemberType]
                                            await component.click()  # type: ignore[reportUnknownMemberType]
                                            discord_logger.info(f"Watered tree at {message.created_at}")
                                            return

    if Lego.user in message.mentions:
        discord_logger.info(f"Message from {message.author}: {message.content}")

    await Lego.process_commands(message)


@Lego.event
async def on_ready():
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


if __name__ == "__main__":
    clean_logs()
    if helpers_check:
        get_help()
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
    if token is None:
        raise ValueError("TOKEN environment variable is missing.")
    Lego.run(token)
