import asyncio
from pathlib import Path
from typing import Any, Optional, Iterable, List, TypedDict, Dict

import discord
from discord.ext import commands
from discord import Message

from utils.utils import activity, code_logger, discord_logger, load_activity, save_activity


activity_file = Path(activity)
activity_file.parent.mkdir(parents=True, exist_ok=True)


class Reactions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        activity = load_activity()
        self.reaction_config = activity.get("reaction", {})
        self.old_reaction_config = activity.get("reaction_old", {})

    @commands.command(
        name='react',
        usage='?r :emoji1: :emoji2: ... [@user1] [@user2] ...',
        help='Start auto-reacting with multiple emojis, optionally filtered by users.',
        aliases=['r']
    )
    async def react(self, ctx: commands.Context[Any], *args: Iterable[str]) -> None:
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use react.")
            return

        if not args:
            try:
                await ctx.send("Please provide at least one emoji to react with.", delete_after=5)
                return
            except Exception as e:
                code_logger.error(f"An error has occurred trying to respond {e}", exc_info=True)

        emojis: List[str] = []
        user_ids: List[int] = []

        for arg in args:
            try:
                s = str(arg)
                if s.startswith('<@') and s.endswith('>'):
                    try:
                        user_id = int(s.strip('<@!>'))
                        user_ids.append(user_id)
                    except ValueError:
                        continue
                else:
                    emojis.append(s)
            except Exception as e:
                code_logger.error(f"An error has occurred trying to respond {e}", exc_info=True)

        if len(emojis) > 10:
            try:
                emojis = emojis[:10]
                await ctx.send("Limited to 10 emojis maximum.", delete_after=5)
                return
            except Exception as e:
                code_logger.error(f"An error has occurred trying to respond {e}", exc_info=True)

        if not emojis:
            try:
                await ctx.send("No valid emojis provided.", delete_after=5)
                return
            except Exception as e:
                code_logger.error(f"An error has occurred trying to respond {e}", exc_info=True)

        activity = load_activity()
        reactions = activity.get("reactions", {})

        existing_ids = [int(k) for k in reactions.keys() if k.isdigit()]
        next_id = str(max(existing_ids) + 1 if existing_ids else 1)

        reactions[next_id] = {
            "active": True,
            "reaction": ", ".join(emojis),
            "target_user_ids": user_ids if user_ids else None,
            "guild_id": None if user_ids else (ctx.guild.id if ctx.guild else None)
        }

        activity["reactions"] = reactions
        save_activity(activity)

        try:
            await ctx.message.edit(content=f"This reaction number is set to {next_id}")
            await asyncio.sleep(3)
            await ctx.message.delete()
        except discord.HTTPException as e:
            code_logger.warning(f"Failed to edit message: {e}", exc_info=True)

    @commands.command(
        name='reactstop',
        usage='?rs <id>',
        help='Stop auto-reacting for a specific reaction ID.',
        aliases=['rs']
    )
    async def reactstop(self, ctx: commands.Context[Any], reaction_id: Optional[str] = None):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use reactstop.")
            return

        if not reaction_id:
            try:
                await ctx.send("You must specify a reaction ID to stop.", delete_after=5)
                return
            except Exception as e:
                code_logger.error(f"An error has occurred trying to respond {e}", exc_info=True)

        activity = load_activity()
        reactions = activity.get("reactions", {})

        if reaction_id not in reactions:
            try:
                await ctx.send(f"No reaction with ID `{reaction_id}` found.", delete_after=5)
                return
            except Exception as e:
                code_logger.error(f"An error has occurred trying to respond {e}", exc_info=True)

        reactions[reaction_id]["active"] = False
        activity["reactions"] = reactions
        save_activity(activity)

        channel_name = getattr(ctx.channel, "name", None)
        if isinstance(channel_name, str):
            discord_logger.info(f"Reaction ID {reaction_id} disabled in #{channel_name}")
        else:
            discord_logger.info(f"Reaction ID {reaction_id} disabled in an unknown channel")

        await ctx.message.delete()

    @commands.command(
        name='reactold',
        usage='?ro :emoji: @optionaluser',
        help='Add reactions to past messages using the specified emoji, optionally filtered by user.',
        aliases=['ro']
    )
    async def reactold(self, ctx: commands.Context[Any], emoji: str, user: Optional[discord.User] = None, limit: int = 100):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use reactold.")
            return

        class OldReactionConfig(TypedDict, total=False):
            active: bool
            reaction: str
            channel_id: int
            target_user_id: Optional[int]

        self.old_reaction_config: OldReactionConfig = {
            "active": True,
            "reaction": emoji,
            "channel_id": ctx.channel.id,
            "target_user_id": user.id if user else None,
        }

        activity = load_activity()
        activity["reaction_old"] = self.old_reaction_config
        save_activity(activity)

        channel_name = getattr(ctx.channel, "name", None)
        discord_logger.info(f"Processing old messages with reaction: {emoji} in {channel_name} (user: {user}, limit: {limit})")

        try:
            await ctx.message.delete()
        except Exception as e:
            code_logger.error(f"An error has occurred trying to respond {e}", exc_info=True)

        counter = 0
        try:
            async for message in ctx.channel.history(limit=limit):
                if message.author == self.bot.user:
                    continue

                user_match = (
                    self.old_reaction_config.get("target_user_id") is None or message.author.id == self.old_reaction_config["target_user_id"]
                )

                if user_match:
                    try:
                        await message.add_reaction(emoji)
                        counter += 1
                    except discord.HTTPException as e:
                        code_logger.error(f"Failed to react to old message in #{channel_name}: {e}", exc_info=True)

                        if e.code == 50083:
                            discord_logger.info(f"Reached message too old limit after {counter} reactions")
                            break
        except Exception as e:
            code_logger.exception(f"Error processing old messages: {e}", exc_info=True)

        self.old_reaction_config["active"] = False
        activity = load_activity()
        activity["reaction_old"] = self.old_reaction_config

        try:
            save_activity(activity)
            discord_logger.info(f"Completed reactold command, processed {counter} messages")
        except Exception as e:
            code_logger.error(f"An error has occurred trying to save activity, {e}", exc_info=True)

    @commands.command(
        name='reactoldstop',
        usage='?ros',
        help='Stop processing old messages for reactions.',
        aliases=['ros']
    )
    async def reactoldstop(self, ctx: commands.Context[Any]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use reactoldstop.")
            return

        self.old_reaction_config = {"active": False}
        activity = load_activity()
        activity["reaction_old"] = self.old_reaction_config
        save_activity(activity)
        channel_name = getattr(ctx.channel, "name", None)
        discord_logger.info(f"Old reaction processing stopped in {channel_name}")
        await ctx.message.delete()

    @commands.command(
        name='reactremove',
        usage='?rr',
        help='Remove the bot’s own reactions from past messages.',
        aliases=['rr']
    )
    async def reactremove(self, ctx: commands.Context[Any]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use reactremove.")
            return

        self.remove_reaction_config: Dict[str, Any] = {}

        activity = load_activity()
        activity["reaction_remove"] = self.remove_reaction_config
        save_activity(activity)

        channel_name = getattr(ctx.channel, "name", None)
        discord_logger.info(f"Removing all bot reactions from messages in #{channel_name}")
        await ctx.message.delete()

        counter = 0
        try:
            async for message in ctx.channel.history():
                if message.author == self.bot.user:
                    continue
                try:
                    for reaction in message.reactions:
                        async for user in reaction.users():
                            if user == self.bot.user and self.bot.user:
                                await message.remove_reaction(reaction.emoji, self.bot.user)
                                counter += 1
                                await asyncio.sleep(1)
                                discord_logger.debug(f"Removed reaction {reaction.emoji} from message in #{channel_name}")
                                break
                except discord.HTTPException as e:
                    discord_logger.warning(f"Failed to remove reaction in #{channel_name}: {e}")
                    if e.code == 50083:
                        discord_logger.info(f"Reached message too old limit after {counter} removals")
                        break
        except Exception as e:
            discord_logger.exception(f"Error removing reactions: {e}")

        self.remove_reaction_config["active"] = False
        activity = load_activity()
        activity["reaction_remove"] = self.remove_reaction_config
        save_activity(activity)
        discord_logger.info(f"Completed reactremove command, removed {counter} reactions")

    @commands.command(
        name='reactstopremove',
        usage='?rsr',
        help='Stop removing the bot’s reactions from messages.',
        aliases=['rsr']
    )
    async def reactstopremove(self, ctx: commands.Context[Any]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author.id} tried to use reactstopremove.")
            return

        self.remove_reaction_config = {"active": False}
        activity = load_activity()
        activity["reaction_remove"] = self.remove_reaction_config
        save_activity(activity)
        channel_name = getattr(ctx.channel, "name", None)
        discord_logger.info(f"Reaction removal stopped in #{channel_name}")
        await ctx.message.delete()

    @commands.command(name="reactlist", aliases=["rl"], help="Lists all configured reactions.", usage="?rl")
    async def reactlist(self, ctx: commands.Context[Any]):
        if ctx.author != self.bot.user:
            discord_logger.info(f"Unauthorized user {ctx.author} (ID: {ctx.author.id}) tried to use reactlist.")
            return

        await ctx.message.delete()

        data = load_activity()
        reactions = data.get("reactions", {})

        if not reactions:
            await ctx.send("```No reactions configured.```", delete_after=5)
            return

        output = ["```", "Configured Reactions:"]
        box_width = 50

        for key, val in reactions.items():
            output.append("+" + "-" * box_width + "+")
            output.append(f"| id: {key}{' ' * (box_width - len(f'id: {key}') - 1)}|")

            active_status = f"active: {val.get('active', False)}"
            output.append(f"| {active_status}{' ' * (box_width - len(active_status) - 1)}|")

            guild_id = f"guild_id: {val.get('guild_id') or 'None'}"
            output.append(f"| {guild_id}{' ' * (box_width - len(guild_id) - 1)}|")

            target_ids = val.get("target_user_ids")
            targets = ', '.join(map(str, target_ids)) if target_ids else "None"
            target_line = f"targets: {targets}"
            if len(target_line) <= box_width - 2:
                output.append(f"| {target_line}{' ' * (box_width - len(target_line) - 1)}|")
            else:
                chunks = [targets[i:i + box_width - 10] for i in range(0, len(targets), box_width - 10)]
                output.append(f"| targets: {chunks[0]}{' ' * (box_width - len('targets: ' + chunks[0]) - 1)}|")
                for chunk in chunks[1:]:
                    output.append(f"| {' ' * 9}{chunk}{' ' * (box_width - len(chunk) - 9 - 1)}|")

            emojis = val.get("emojis", [])
            emoji_line = f"emojis: {', '.join(emojis)}"
            if len(emoji_line) <= box_width - 2:
                output.append(f"| {emoji_line}{' ' * (box_width - len(emoji_line) - 1)}|")
            else:
                chunks = [emoji_line[i:i + box_width - 10] for i in range(0, len(emoji_line), box_width - 10)]
                output.append(f"| emojis: {chunks[0]}{' ' * (box_width - len('emojis: ' + chunks[0]) - 1)}|")
                for chunk in chunks[1:]:
                    output.append(f"| {' ' * 8}{chunk}{' ' * (box_width - len(chunk) - 8 - 1)}|")

            output.append("+" + "-" * box_width + "+")

        output.append("```")
        await ctx.send("\n".join(output), delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user or message.author.bot:
            return

        activity = load_activity()
        reactions = activity.get("reactions", {})

        for reaction_data in reactions.values():
            if not reaction_data.get("active", False):
                continue

            target_users = reaction_data.get("target_user_ids")
            guild_limit = reaction_data.get("guild_id")

            if guild_limit is not None:
                if not message.guild or message.guild.id != guild_limit:
                    continue

            if target_users is not None and message.author.id not in target_users:
                continue

            emojis = reaction_data.get("emojis")
            if not emojis:
                continue

            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)

                    ch = message.channel
                    ch_name = getattr(ch, 'name', None)
                    if isinstance(ch_name, str):
                        name = f"#{ch_name}"
                    else:
                        recipient = getattr(ch, 'recipient', ch)
                        name = f"DM:{getattr(recipient, 'id', 'unknown')}"
                    discord_logger.debug(f"Reacted to message in {name} with {emoji}")

                except discord.HTTPException as e:
                    ch = message.channel
                    ch_name = getattr(ch, 'name', None)
                    if isinstance(ch_name, str):
                        name = f"#{ch_name}"
                    else:
                        recipient = getattr(ch, 'recipient', ch)
                        name = f"DM:{getattr(recipient, 'id', 'unknown')}"
                    discord_logger.warning(f"Failed to react in {name} with {emoji}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Reactions(bot))
