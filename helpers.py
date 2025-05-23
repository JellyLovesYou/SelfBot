import asyncio
import os
import pathlib
import random
import string
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Optional, TypedDict, List
from asyncio import Task

from discord import TextChannel, HTTPException, DiscordServerError
from discord.ext import commands
from dotenv import load_dotenv

from utils.utils import code_logger, delay, discord_logger, env, load_activity, prefix

load_dotenv(dotenv_path=Path(env))
TOKENS = [os.getenv(f'discord_token_{i}') or "" for i in range(1, 6)]


class SendingConfig(TypedDict, total=False):
    channel_id: int
    text: str
    length: int
    active: bool


class Helpers:
    def __init__(self, token: str):
        self.token = token
        self.bot = commands.Bot(command_prefix=prefix, self_bot=True)
        self.send_task: Optional[Task[None]] = None
        self.last_config: Optional[SendingConfig] = None

        self.bot.event(self.on_ready)

    async def on_ready(self):
        discord_logger.info(f'Helper {self.bot.user} is active')
        asyncio.create_task(self.monitor_activity())
        asyncio.create_task(self.monitor_for_shutdown())

    async def send_messages(self, config: Mapping[str, Any]):
        channel_id = config.get("channel id")
        text = config.get("text")
        length = config.get("length", 10)
        retries = config.get("retries", 3)

        characters = string.ascii_letters + string.digits

        if channel_id is None:
            code_logger.error("No channel_id provided in config", exc_info=True)
            return

        try:
            channel = await self.bot.fetch_channel(channel_id)
            if not isinstance(channel, TextChannel):
                code_logger.error(f"Channel with ID {channel_id} is not a TextChannel", exc_info=True)
                return

            while True:
                content = text or ''.join(random.choices(characters, k=length))
                for attempt in range(retries):
                    try:
                        await channel.send(content)
                        break
                    except (HTTPException, DiscordServerError) as e:
                        code_logger.warning(f"Send attempt {attempt+1}/{retries} failed: {e}")
                        if attempt < retries - 1:
                            await asyncio.sleep(delay * (2 ** attempt))
                        else:
                            raise
                await asyncio.sleep(delay)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            code_logger.error(f"Send error: {e}", exc_info=True)

    async def monitor_activity(self):
        while not self.bot.is_closed():
            await asyncio.sleep(2)
            config: Optional[SendingConfig] = load_activity().get("sending")

            if config != self.last_config:
                self.last_config = config

                if self.send_task:
                    self.send_task.cancel()
                    try:
                        await self.send_task
                    except asyncio.CancelledError:
                        pass

                if config is not None and config.get("active", False):
                    self.send_task = asyncio.create_task(self.send_messages(config))
                else:
                    self.send_task = None

    async def monitor_for_shutdown(self):
        while not self.bot.is_closed():
            if pathlib.Path("restart.signal").exists():
                await self.bot.close()
            await asyncio.sleep(2)

    async def start(self):
        try:
            await self.bot.start(self.token)
        except Exception as e:
            code_logger.error(f"Bot error: {e}, token: {self.token}", exc_info=True)
        finally:
            await self.bot.close()


def run_worker(token: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    worker = Helpers(token)
    try:
        loop.run_until_complete(worker.start())
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def start_all_workers() -> None:
    threads: List[threading.Thread] = []
    for token in TOKENS:
        thread = threading.Thread(target=run_worker, args=(token,), daemon=True)
        threads.append(thread)
        thread.start()
        time.sleep(2)

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    start_all_workers()
