import asyncio
import ctypes
import difflib
import json
import os
import pathlib
import re
import subprocess
import time
import atexit
from pathlib import Path
from typing import List, Optional

import discord
from discord import Message, TextChannel
from discord.ext import commands
from dotenv import load_dotenv

from utils.telecom import text, water, p2verification, fish, start_browser
from utils.data import p2verification_message
from utils.utils import clean_logs, load_activity, save_activity, code_logger, discord_logger, pokemon_logger, tree_logger, fish_logger, env, prefix


config_path = Path("data/config/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)


with open(config_path) as f:
    config = json.load(f)

bot_version = str(config['main']['version'])
nickname = str(config['main']['nickname'])
catching_check = bool(config['main']['catching?'])
p2assistant_check = bool(config['main']['p2assistant?'])
helpers_check = bool(config['main']['helpers?'])
solving_check = bool(config['main']['solving?'])
sniping_check = bool(config['main']['sniping?'])
fishing_check = bool(config['main']['fishing?'])
user_id = int(config['main']['user id'])
watch_id = int(config['ids']['watch id'])
fish_watch_id = int(config['ids']['fish id'])
mention_id = int(config['ids']['mention id'])
tree_message_id = int(config['ids']['tree'])
tree_channel_id = int(config['ids']['tree channel'])
fishing_channel = int(config['ids']['fish channel'])
pokemon_text_check = bool(config['text']['pokemon'])
fishing_text_check = bool(config['text']['fishing'])
helpers = str(config['paths']['helpers'])
restart = str(config['paths']['restart'])
pokemon = str(config['paths']['pokemon'])
session = str(config['paths']['session'])
venv = str(config['paths']['venv'])
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
tree_monitor_task = None
fishing_loop_check = None
fishing_clear = True
helper_proc = None


with open(pokemon, "r", encoding='utf-8') as f:
    pokemon_list = [line.strip() for line in f if line.strip()]


if pathlib.Path(restart).exists():
    pathlib.Path(restart).unlink()


def stop_sending():
    activity_data = load_activity()

    if activity_data and activity_data.get("sending", {}).get("active"):
        activity_data['sending']['active'] = False
        save_activity(activity_data)
        pokemon_logger.info("Stopped 'sending' activity.")


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


async def start_tree_monitor():
    global tree_monitor_task
    if tree_monitor_task is None or tree_monitor_task.done():
        tree_monitor_task = asyncio.create_task(tree_monitor_loop())
        tree_logger.info("Tree monitor loop task created")
    else:
        tree_logger.info("Tree monitor loop already running")


async def tree_monitor_loop():
    tree_logger.info("Tree monitor loop started")
    await Lego.wait_until_ready()
    while True:
        try:
            channel_raw = Lego.get_channel(tree_channel_id)
            if not isinstance(channel_raw, TextChannel):
                code_logger.error("Channel not found or wrong type, exiting loop", exc_info=True)
                return
            channel = channel_raw

            message = await channel.fetch_message(tree_message_id)
            embed_content = message.embeds[0].description or ""

            if "Ready to be watered!" in embed_content:
                last_watered_match = re.search(r"Last watered by: <@!?(\d+)>", embed_content)
                last_watered_user_id = int(last_watered_match.group(1)) if last_watered_match else None
                bot_user_id = Lego.user.id if Lego.user else None

                if last_watered_user_id != bot_user_id:
                    water()
                    tree_logger.info(f"Tree watered, sleeping for 300s at {time.strftime('%X')}.")
                    await asyncio.sleep(120)
                    tree_logger.info(f"Woke up at {time.strftime('%X')}")
                    continue
                else:
                    tree_logger.info(f"Tree already watered, Sleeping for 300s at {time.strftime('%X')}.")
                    await asyncio.sleep(120)
                    tree_logger.info(f"Woke up at {time.strftime('%X')}")
                    continue
            else:
                tree_logger.info("Tree not ready yet.")

        except Exception as e:
            code_logger.error(f"Error in tree monitor loop: {e}", exc_info=True)

        tree_logger.info(f"Sleeping for 30s at {time.strftime('%X')}")
        await asyncio.sleep(30)


async def start_fishing_loop():
    global fishing_check
    global fishing_clear
    global fishing_loop_check
    if fishing_check and fishing_clear:
        if fishing_loop_check is None or fishing_loop_check.done():
            fishing_loop_check = asyncio.create_task(fishing_loop())
            fish_logger.info("Fish monitor loop task created")
        else:
            fish_logger.info("Fish monitor loop already running")


async def fishing_loop():
    global fishing_check
    global fishing_clear
    if fishing_check and fishing_clear:
        fish_logger.info("Fish monitor loop started")
        await Lego.wait_until_ready()
        await start_browser()
        while fishing_clear:
            try:
                fish_logger.info("Fish called")
                await fish()
                await asyncio.sleep(5)
                fish_logger.info("waiting 5s")
            except asyncio.CancelledError:
                fish_logger.info("Fishing fish loop cancelled.")


@Lego.event
async def on_message(message: discord.Message):
    global catching
    global last_help_time
    global already_triggered
    global fishing_clear
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
                    pokemon_logger.info(f"catching_check type: {type(catching_check)}, value: {repr(catching_check)}")
                    pokemon_logger.info(f'{p2verification_message}')
                    assert isinstance(catching_check, bool), f"Expected boolean, got {type(catching_check)}: {repr(catching_check)}"

                    if not already_triggered:
                        pokemon_logger.info(f"{catching_check} and not {already_triggered} check success.")
                        try:
                            if solving_check:
                                pokemon_logger.info("This part was gotten too aswell.")
                                p2verification()
                                catching = False
                                already_triggered = True

                            elif pokemon_text_check:
                                await text(p2verification_message)
                                pokemon_logger.info("A text was sent")
                                stop_sending()
                                catching = False
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

    if sniping_check:
        if message.embeds:
            for embed in message.embeds:
                embed_content = str(embed.title or "") + str(embed.description or "")
                if "You received a gift" in embed_content:
                    discord_logger.info("Nitro spotted")

    if message.author.id == fish_watch_id:
        if fishing_check:
            if message.embeds:
                for embed in message.embeds:
                    embed_content = str(embed.title or "") + str(embed.description or "")
                    if "Anti-bot" in embed_content:
                        try:
                            fishing_clear = False
                            fish_logger.warning("Fisher is asking for verification")

                            if fishing_text_check:
                                await text("Virtual Fisher is asking for verification")
                                fish_logger.info("A text was sent")
                                stop_sending()

                        except Exception as e:
                            code_logger.error(f"An exception occurred while appending fishing.txt, {e}", exc_info=True)

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

    try:
        session_id = Lego.ws.session_id
        with open(session, "w") as f:
            f.write(str(session_id))
    except Exception as e:
        code_logger.error(f"An error has occured while trying to update {session}, {e}", exc_info=True)

    try:
        await start_tree_monitor()
        await start_fishing_loop()
    except Exception as e:
        code_logger.error(f"There was an error trying to monitor the tree, {e}", exc_info=True)


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
