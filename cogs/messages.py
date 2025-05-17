import asyncio
import os
import random
import re
import string
from typing import Any, Dict, Optional

import discord
from discord.abc import Messageable
from discord.ext import commands

from utils.utils import code_logger, delay, discord_logger, load_activity, log_paths, save_activity


class Messages(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cogs_dir = os.path.join(os.path.dirname(__file__))
        self.send_task = None

        self.activities = load_activity()
        self.sending: Dict[str, Any] = self.activities.get("sending") or {}

        self.characters = string.ascii_letters + string.digits
        self.text = self.sending.get("text")
        self.length = self.sending.get("length", 10)
        self.channel_id_raw = self.sending.get("channel id")
        try:
            self.channel_id = int(self.channel_id_raw) if self.channel_id_raw is not None else None
        except (ValueError, TypeError):
            self.channel_id = None
            code_logger.error(f"Invalid channel_id_raw: {self.channel_id_raw}", exc_info=True)

        bot.loop.create_task(self.resume_task())

    async def send_messages(self):
        if self.channel_id is None:
            code_logger.error("Channel ID is None; aborting send_messages", exc_info=True)
            return

        try:
            channel = await self.bot.fetch_channel(self.channel_id)
        except discord.NotFound:
            code_logger.error(f"Channel ID {self.channel_id} not found", exc_info=True)
            return
        except discord.Forbidden:
            code_logger.error(f"Forbidden access to channel {self.channel_id}", exc_info=True)
            return
        except Exception as e:
            code_logger.error(f"Unexpected error fetching channel: {e}", exc_info=True)
            return

        if not isinstance(channel, Messageable):
            code_logger.error(f"Channel {self.channel_id} is not messageable", exc_info=True)
            return

        try:
            while True:
                success = False
                for attempt in range(3):
                    try:
                        content = self.text or ''.join(random.choices(self.characters, k=self.length))
                        await channel.send(content)
                        success = True
                        await asyncio.sleep(delay)
                        break
                    except discord.HTTPException as e:
                        if e.status == 503:
                            await asyncio.sleep(delay ** attempt)
                            code_logger.info(f"Status 503, retrying attempt {attempt}")
                        elif e.status == 404:
                            await asyncio.sleep(delay ** attempt)
                            code_logger.info(f"Status 503, retrying attempt {attempt}")
                        else:
                            code_logger.error(f"Discord HTTP exception: {e.status}", exc_info=True)
                            break
                    except Exception as e:
                        code_logger.error(f"Error sending messages: {e}", exc_info=True)
                        break
                if not success:
                    await asyncio.sleep(delay)

                await asyncio.sleep(0)

        except asyncio.CancelledError:
            discord_logger.info("send_messages task was cancelled.")
            raise

        except Exception as e:
            code_logger.error(f"Error sending messages: {e}", exc_info=True)

    async def resume_task(self):
        await self.bot.wait_until_ready()
        if not self.sending or not self.sending.get("active", False):
            return
        channel = self.bot.get_channel(self.channel_id) if self.channel_id is not None else None
        if channel is None:
            code_logger.error(f"Channel ID {self.channel_id} not found or invalid", exc_info=True)
            return

        if not isinstance(channel, discord.TextChannel):
            code_logger.error(f"Channel ID {self.channel_id} is not a TextChannel", exc_info=True)
            return

        self.send_task = asyncio.create_task(self.send_messages())

    @commands.command(name='send', help='Sends random messages to the specified channel.', usage='?send <text>')
    async def send(self, ctx: commands.Context[Any], *, text: str = None):  # type: ignore
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use send.")
            return

        if self.send_task is not None and not self.send_task.done():
            self.send_task.cancel()
            try:
                await self.send_task
            except asyncio.CancelledError:
                pass

        self.activities["sending"] = {
            "active": True,
            "text": text,
            "length": 10,
            "channel id": ctx.channel.id
        }
        save_activity(self.activities)

        self.sending = self.activities["sending"]
        self.text = text
        self.length = 10
        self.channel_id = ctx.channel.id

        self.send_task = asyncio.create_task(self.send_messages())
        await ctx.message.delete()

    @commands.command(
        name='stop',
        help='Stops sending random messages.',
        usage='?stop'
    )
    async def stop(self, ctx: commands.Context[Any]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use stop.")
            return

        if self.send_task and not self.send_task.done():
            self.send_task.cancel()
            self.send_task = None

            activities = load_activity()
            if "sending" in activities:
                activities["sending"]["active"] = False
                save_activity(activities)

            await ctx.send("Okay, I'll stop...")
        else:
            await ctx.send("I wasn't doing anything.")

        await ctx.message.delete()

    @commands.command(
        name='clear',
        help='Clears a specified number of bot messages in the current channel.',
        usage='?clear <limit>'
    )
    async def clear(self, ctx: commands.Context[Any], limit: int):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author} (ID: {ctx.author.id}) tried to use clear.")
            return

        deleted = 0
        async for message in ctx.channel.history(limit=limit):
            if message.author == self.bot.user:
                try:
                    await message.delete()
                    deleted += 1
                except discord.HTTPException as e:
                    discord_logger.warning(f"Failed to delete message: {e}")

        try:
            await ctx.message.delete()
            await ctx.send(f"Deleted {deleted} bot messages.", delete_after=3)
        except discord.HTTPException:
            pass

    @commands.command(
        name='h',
        help='Shows available command categories or lists commands within a category.',
        usage='?h [category]'
    )
    async def h(self, ctx: commands.Context[Any], category: Optional[str]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author} (ID: {ctx.author.id}) tried to use help.")
            return

        await ctx.message.delete()

        if category is None:
            try:
                categories = [
                    f[:-3] for f in os.listdir(self.cogs_dir)
                    if f.endswith(".py") and not f.startswith("__")
                ]
                await ctx.send("```\nPlease choose a category:\n" + "\n".join(sorted(categories)) + "\n```", delete_after=5)
                return
            except Exception as e:
                code_logger.error(f"An error occurred {e}.", exc_info=True)
                return

        path = os.path.join(self.cogs_dir, f"{category}.py")
        if not os.path.isfile(path):
            await ctx.send("Unknown category.", delete_after=3)
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                contents = f.read()
        except Exception as e:
            code_logger.error(f"Failed to read cog: {e}", exc_info=True)
            return

        pattern = re.compile(r'@commands\.command\s*\(([^)]*)\).*?\n\s*async\s+def\s+(\w+)', re.DOTALL)
        matches = pattern.findall(contents)

        if not matches:
            await ctx.send(f"No commands found in category '{category}'.", delete_after=3)
            return

        output: list[str] = []
        box_width = 30

        for args, func in matches:
            name = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", args)
            help_ = re.search(r"help\s*=\s*['\"]([^'\"]*)['\"]", args)
            usage = re.search(r"usage\s*=\s*['\"]([^'\"]+)['\"]", args)
            aliases = re.search(r"aliases\s*=\s*\[([^\]]*)\]", args)

            name_val = name.group(1) if name else func
            help_val = help_.group(1) if help_ else ""
            usage_val = usage.group(1) if usage else "No usage specified"

            output.append("+" + "-" * box_width + "+")
            output.append(f"| name: {name_val}{' ' * (box_width - len('name: ' + name_val) - 1)}|")

            if aliases:
                alias_list = ", ".join(a.strip().strip('"').strip("'") for a in aliases.group(1).split(",") if a.strip())
                alias_text = f"aliases: '{alias_list}'"
            else:
                alias_text = "aliases: None"

            output.append(f"| {alias_text}{' ' * (box_width - len(alias_text) - 1)}|")

            help_lines: list[str] = []
            help_prefix = "help: "
            remaining_help = help_val

            first_line_max = box_width - len(help_prefix) - 1
            if len(remaining_help) <= first_line_max:
                help_lines.append(f"| {help_prefix}{remaining_help}{' ' * (first_line_max - len(remaining_help))}|")
                remaining_help = ""
            else:
                space_pos = remaining_help[:first_line_max].rfind(' ')
                if space_pos == -1:
                    space_pos = first_line_max

                help_lines.append(f"| {help_prefix}{remaining_help[:space_pos]}{' ' * (first_line_max - len(remaining_help[:space_pos]))}|")
                remaining_help = remaining_help[space_pos:].strip()

            indent = " " * (len(help_prefix))
            cont_line_max = box_width - len(indent) - 2

            while remaining_help:
                if len(remaining_help) <= cont_line_max:
                    help_lines.append(f"| {indent}{remaining_help}{' ' * (cont_line_max - len(remaining_help))}|")
                    break
                else:
                    space_pos = remaining_help[:cont_line_max].rfind(' ')
                    if space_pos == -1:
                        space_pos = cont_line_max

                    help_lines.append(f"| {indent}{remaining_help[:space_pos]}{' ' * (cont_line_max - len(remaining_help[:space_pos]))}|")
                    remaining_help = remaining_help[space_pos:].strip()

            output.extend(help_lines)

            usage_text = f"usage: {usage_val}"
            output.append(f"| {usage_text}{' ' * (box_width - len(usage_text) - 1)}|")

            output.append("+" + "-" * box_width + "+")

        message = f"```\n{category.capitalize()} commands:\n" + "\n".join(output) + "\n```"
        await ctx.send(message, delete_after=10)

    @commands.command(
        name='ping',
        help='Checks bot latency.',
        usage='?ping'
    )
    async def ping(self, ctx: commands.Context[Any]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use ping.")
            return

        start = discord.utils.utcnow()
        message = await ctx.send("Pinging...")
        end = discord.utils.utcnow()

        latency = (end - start).total_seconds() * 1000
        await message.edit(content=f"Pong! Response time: `{latency:.2f}ms`", delete_after=3)
        await ctx.message.delete()

    @commands.command(name="logs")
    async def logs(self, ctx: commands.Context[Any], log_type: str):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use ping.")
            return

        await ctx.message.delete()
        log_type = log_type.lower()
        path = log_paths.get(log_type)

        if not path or not os.path.exists(path):
            await ctx.send(f"Unknown or missing log type: `{log_type}`.")
            return

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            await ctx.send(f"Failed to read log: `{e}`")
            return

        if len(content) < 1900:
            await ctx.send(f"```txt\n{content}```", delete_after=15)
        else:
            await ctx.send(file=discord.File(path, filename=os.path.basename(path)), delete_after=15)


async def setup(bot: commands.Bot):
    await bot.add_cog(Messages(bot))
