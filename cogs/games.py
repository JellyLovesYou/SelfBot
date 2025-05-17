import asyncio
import random
from typing import Any

from discord import Member, Message, User
from discord.ext import commands

from utils.data import (
    addresses,
    ethnicities,
    female_names,
    last_names,
    male_names,
    nationalities,
    random_gender,
    random_info,
    races,
    sexualities,
)
from utils.random_utils import (
    generate_random_age,
    generate_random_birthday,
    get_balance,
    get_height,
)
from utils.utils import discord_logger, load_activity, save_activity


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name='dox',
        help='sends a random, fake and funny Dox message',
        usage='?dox @user'
    )
    async def dox(self, ctx: commands.Context[commands.Bot], user: User | Member | None = None) -> None:
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use reactstop.")
            return

        await ctx.message.delete()
        if user is None:
            user = ctx.author

        gender = random.choice(random_gender)
        if gender == "Male":
            name = random.choice(male_names)
        elif gender == "Female":
            name = random.choice(female_names)
        else:
            name = random.choice(male_names + female_names)

        lastname = random.choice(last_names)
        address = random.choice(addresses)
        race = random.choice(races)
        nationality = random.choice(nationalities)
        sexuality = random.choice(sexualities)
        ethnicity = random.choice(ethnicities)
        age = generate_random_age()
        birthday = generate_random_birthday(age).strftime('%Y-%m-%d')
        fun_fact = random.choice(random_info)
        balance = get_balance()
        height = get_height()

        message = (
            f"```\n"
            f"{user.name}'s Dox:\n\n"
            f"Name:        {name} {lastname}\n"
            f"Gender:      {gender}\n"
            f"Height:      {height}\n"
            f"Age:         {age}\n"
            f"Birthday:    {birthday}\n"
            f"Nationality: {nationality}\n"
            f"Race:        {race}\n"
            f"Ethnicity:   {ethnicity}\n"
            f"Sexuality:   {sexuality}\n"
            f"Address:     {address}\n"
            f"Net Value:   ${balance}\n"
            f"Fun Fact:    {fun_fact}\n"
            f"```\n"
        )

        sent_message = await ctx.send(message)
        await asyncio.sleep(25)
        await sent_message.delete()

    @commands.command(
        name='mimic',
        usage='?m @user [:emoji:]',
        help='Repeat messages from a user in quotes, optionally with an emoji.',
        aliases=['m']
    )
    async def mimic(self, ctx: commands.Context[Any], *args: str) -> None:
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use mimic.")
            return

        if not args:
            await ctx.send("Usage: ?mimic @user [:emoji:]", delete_after=5)
            return

        emoji = None
        user_id = None

        for arg in args:
            if arg.startswith('<@') and arg.endswith('>'):
                try:
                    user_id = int(arg.strip('<@!>'))
                except ValueError:
                    continue
            else:
                emoji = arg

        if user_id is None:
            await ctx.send("No valid user mentioned.", delete_after=5)
            return

        activity = load_activity()
        activity["mimic"] = {
            "target_user_id": user_id,
            "emoji": emoji,
            "guild_id": ctx.guild.id if ctx.guild else None
        }
        save_activity(activity)

        await ctx.message.edit(content=f"Mimicking <@{user_id}>{' with ' + emoji if emoji else ''}")

    @commands.command(
        name='mimicstop',
        usage='?ms',
        help='Stop mimicking a user.',
        aliases=['ms']
    )
    async def mimicstop(self, ctx: commands.Context[Any]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use mimicstop.")
            return

        activity = load_activity()
        activity.pop("mimic", None)
        save_activity(activity)

        await ctx.message.edit(content="Mimic disabled.")

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot or message.author == self.bot.user:
            return

        activity = load_activity()
        mimic = activity.get("mimic")

        if mimic:
            if mimic.get("guild_id") and (not message.guild or message.guild.id != mimic["guild_id"]):
                return
            if message.author.id == mimic.get("target_user_id"):
                content = f'"{message.content}"'
                if mimic.get("emoji"):
                    content += f' - {mimic["emoji"]}'
                await message.channel.send(content)


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
