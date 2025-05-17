import json
from discord.ext import commands
from pathlib import Path
import logging
import discord
import webbrowser
import random
from typing import Any, Optional


with open(Path("data/config/config.json")) as f:
    config = json.load(f)

activity = config["paths"]["activity"]
env = config['paths']['env']
prefix = config['main']['prefix']
delay = round(random.uniform(2, 2.20), 2)
Lego = commands.Bot(command_prefix=prefix, self_bot=True)


def setup_logger(name: str, log_file: Path, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        logger.handlers.clear()

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(filename)s] %(message)s")
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger


log_paths = {
    'code': config['paths']['code logs'],
    'discord': config['paths']['discord logs'],
    'pokemon': config['paths']['pokemon logs'],
    'tree': config['paths']['tree logs']
}

code_logger = setup_logger('code', Path(log_paths['code']))
discord_logger = setup_logger('discord', Path(log_paths['discord']))
pokemon_logger = setup_logger('pokemon', Path(log_paths['pokemon']))
tree_logger = setup_logger("tree", Path(log_paths['tree']))


def clean_logs():
    for path in log_paths.values():
        log_file = Path(path)
        if log_file.is_file():
            with open(log_file, "w"):
                pass


def load_activity() -> dict[str, Any]:
    activity_file = Path(activity)
    while True:
        try:
            if activity_file.exists() and activity_file.stat().st_size > 0:
                with activity_file.open('r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                code_logger.warning("Activity file missing or empty.")
        except json.JSONDecodeError:
            code_logger.warning("Activity file contains invalid JSON, starting fresh.")
        except Exception as e:
            code_logger.exception(f"Failed to load activity file: {e}")
        return {}


def save_activity(activity_data: dict[str, Any]) -> None:
    activity_file = Path(activity)
    try:
        activity_file.parent.mkdir(parents=True, exist_ok=True)
        with activity_file.open('w', encoding='utf-8') as f:
            json.dump(activity_data, f, indent=2)
        code_logger.debug(f"Saved activity: {activity_data}")
    except Exception as e:
        code_logger.exception(f"Failed to save activity: {e}")


async def generate_invite_link(channel: discord.TextChannel) -> Optional[str]:
    try:
        invite: discord.Invite = await channel.create_invite(max_age=300, validate=None)
        return invite.url
    except discord.Forbidden:
        code_logger.error("Permission error: The bot does not have permission to create an invite.", exc_info=True)
        return None


async def join_guild(channel: discord.TextChannel) -> None:
    invite_link = await generate_invite_link(channel)
    if invite_link:
        try:
            webbrowser.open(invite_link)
            discord_logger.info(f"Invite link opened for joining the guild: {invite_link}")
        except Exception as e:
            code_logger.error(f"Error opening invite link: {e}", exc_info=True)
