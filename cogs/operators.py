import asyncio
import os
import sys
from typing import Any

from discord.ext import commands

from utils.utils import discord_logger


class Operators(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name='shutdown',
        help='Shuts the bot down completely.',
        usage='?sd',
        aliases=['sd']
    )
    async def stop(self, ctx: commands.Context[Any]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use stop.")
            return

        await ctx.message.edit(content="Bye bye")
        await asyncio.sleep(3)
        await ctx.message.delete()
        await self.bot.close()
        sys.exit(0)

    @commands.command(
        name='restart',
        help='Restarts the bot and reloads all cogs.',
        usage='?restart'
    )
    async def restart(self, ctx: commands.Context[Any]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use restart.")
            return

        await ctx.message.edit(content="Restarting...")
        await asyncio.sleep(2)
        await ctx.message.delete()
        await self.bot.close()

        os.execl(sys.executable, sys.executable, *sys.argv)


async def setup(bot: commands.Bot):
    await bot.add_cog(Operators(bot))
