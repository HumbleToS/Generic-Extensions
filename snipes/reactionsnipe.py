"""
Copyright 2022-present fretgfr

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations

"""
This module uses the following third party libs installed via pip: asqlite (https://github.com/Rapptz/asqlite)
"""

import datetime
import logging
from dataclasses import dataclass

import asqlite
import discord
from discord.ext import commands, tasks

# If not using all snipe categories, you'll need to bring these items into this file,
# along with making sure the BotUser table is created and handling deleting opted out users data
# from the database (the custom event won't work unless you maintain that logic.)
from .optout import BotUser
from .snipescommon import DB_FILENAME

_logger = logging.getLogger(__name__)

# Maximum age will be TTL_MINUTES * 2
TTL_MINUTES = 5

SETUP_SQL = """
CREATE TABLE IF NOT EXISTS reactionsnipe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    removed_at BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    message_id TEXT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    unicode_codepoint TEXT NULL,
    emoji_url TEXT NULL
)
"""

@dataclass(slots=True)
class ReactionSnipe:
    """Represents a deleted Discord Message"""
    id: int
    removed_at: int
    user_id: int
    message_id: int
    guild_id: int
    channel_id: int
    unicode_codepoint: str
    emoji_url: str

    @classmethod
    async def from_payload(cls, payload: discord.RawReactionActionEvent, /) -> ReactionSnipe:
        """Creates a ReactionSnipe from a given `discord.RawReactionActionEvent`.

        Parameters
        ----------
        payload : discord.RawReactionActionEvent
            The payload to create from

        Returns
        -------
        Self
            The generated ReactionSnipe.
        """
        assert payload.guild_id is not None

        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                removed_at = int(discord.utils.utcnow().timestamp())
                user_id = payload.user_id
                message_id = payload.message_id
                guild_id = payload.guild_id
                channel_id = payload.channel_id

                unicode_codepoint = payload.emoji.name if payload.emoji.is_unicode_emoji() else None
                emoji_url = payload.emoji.url if payload.emoji.is_custom_emoji() else None


                await cur.execute(f"""INSERT INTO reactionsnipe
                (removed_at, user_id, message_id, guild_id, channel_id, unicode_codepoint, emoji_url)
                VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *""", removed_at, user_id, message_id, guild_id, channel_id, unicode_codepoint, emoji_url)
                res = await cur.fetchone()
                await db.commit()

                return cls(**res)

    @classmethod
    async def get_in_channel(cls, channel_id: int, /, *, offset: int = 0) -> ReactionSnipe | None:
        """Gets a ReactionSnipe in a given channel at a given offset.

        This is ordered by deletion time.

        Parameters
        ----------
        channel_id : int
            The channel to retrieve from
        offset : int, optional
            The number of entries back to check, by default 0

        Returns
        -------
        Self | None
            The ReactionSnipe if found, else None.
        """
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM reactionsnipe WHERE channel_id = ? ORDER BY removed_at DESC LIMIT 1 OFFSET ?", channel_id, offset)
                res = await cur.fetchone()

                return cls(**res) if res is not None else None

    @classmethod
    async def delete_one_in(cls, channel_id: int, /, *, offset: int = 0) -> int:
        """Deletes a single database entry in given channel

        Parameters
        ----------
        channel_id : int
            The channel to remove in
        offset : int, optional
            The number of entries to delete back, by default 0

        Returns
        -------
        int
            The number of database entries removed.
        """
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("""DELETE FROM reactionsnipe
                WHERE channel_id = ? AND id IN
                 (SELECT id FROM reactionsnipe WHERE channel_id = ? ORDER BY removed_at DESC LIMIT 1 OFFSET ?)""", channel_id, channel_id, offset)
                await db.commit()

                return cur.get_cursor().rowcount

    @classmethod
    async def delete_all_in(cls, channel_id: int, /) -> int:
        """Removes all items from database with given channel id.

        Parameters
        ----------
        channel_id : int
            The channel id to clear

        Returns
        -------
        int
            The number of removed database entries
        """
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM reactionsnipe WHERE channel_id = ?", channel_id)
                await db.commit()

                return cur.get_cursor().rowcount

    @staticmethod
    async def clear_all_for_user(user_id: int, /) -> int:
        """Removes all snipes for given user_id

        Parameters
        ----------
        user_id : int
            The user_id to clear.

        Returns
        -------
        int
            The number of removed database entries.
        """
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM reactionsnipe WHERE user_id = ?", user_id)
                await db.commit()

                return cur.get_cursor().rowcount

    @property
    def is_custom(self) -> bool:
        """Whether the emoji is custom."""
        return self.emoji_url is not None

    @property
    def is_unicode(self) -> bool:
        """Whether the emoji is unicode."""
        return self.unicode_codepoint is not None

    @property
    def emoji(self) -> str:
        """Returns the emoji asset url or unicode codepoint as applicable."""
        return self.emoji_url if self.emoji_url is not None else self.unicode_codepoint

    @property
    def message_jump_url(self) -> str | None:
        """Jump URL for the message the reaction was removed from."""
        return f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.message_id}"

    @property
    def timestamp(self) -> datetime.datetime:
        """Returns a UTC datetime representing time of deletion"""
        return datetime.datetime.fromtimestamp(self.removed_at, tz=datetime.timezone.utc)

    async def embed(self, ctx: commands.Context) -> discord.Embed:
        """Returns the embed that represents this snipe.

        Parameters
        ----------
        ctx : commands.Context
            The context the snipe is being generated in.

        Returns
        -------
        discord.Embed
            The generated Embed
        """
        author = ctx.guild.get_member(self.user_id) or await ctx.bot.fetch_member(self.user_id)

        embed = discord.Embed(description=f'[Message Reacted To]({self.message_jump_url} "Message Reacted To")', color=discord.Color.blue())
        embed.set_author(name=author, icon_url=author.display_avatar.url)
        embed.timestamp = self.timestamp

        if self.is_custom:
            embed.set_image(url=self.emoji) # emoji is the Asset url for custom emojis
            embed.description += f"\n[Emoji Link]({self.emoji})"

        else:
            embed.description += f"\n{self.emoji}"

        return embed


class ReactionSnipeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        async with asqlite.connect(DB_FILENAME) as db:
            await db.executescript(SETUP_SQL)
        self.delete_snipe_db_purge.start()

    async def cog_unload(self) -> None:
        self.delete_snipe_db_purge.cancel()

    @commands.Cog.listener()
    async def on_optout_status_change(self, user: discord.User, _: bool) -> None:
        """Custom event handler for opt out status changes

        Parameters
        ----------
        user : discord.User
            The user whose opt out status changed
        _ : bool
            The new opt out status
        """
        num_deleted = await ReactionSnipe.clear_all_for_user(user.id)
        _logger.info("Processed reactionsnipe clear for %s, removed %d reactionsnipes.", str(user), num_deleted)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None: return
        if await BotUser.is_opt_out(payload.user_id): return

        _logger.debug("Processing reaction remove in channel with id %d", payload.channel_id)
        await ReactionSnipe.from_payload(payload)

    @commands.command()
    @commands.guild_only()
    async def rsnipe(self, ctx: commands.Context, num_back: int = 0) -> None:
        """Snipes a removed reaction in current channel."""
        snipe = await ReactionSnipe.get_in_channel(ctx.channel.id, offset=num_back)

        if snipe:
            await ctx.send(embed=await snipe.embed(ctx))
        else:
            await ctx.send("No snipe found.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def rmrsnipe(self, ctx: commands.Context, num_back: int = 0) -> None:
        """Removes a reaction snipe in current channel."""
        num_deleted = await ReactionSnipe.delete_one_in(ctx.channel.id, offset=num_back)

        if num_deleted > 0:
            await ctx.send(f"Deleted snipe at index {num_back} in {ctx.channel.mention}")
        else:
            await ctx.send(f"I didn't find anything to delete in {ctx.channel.mention} at index {num_back}")

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    async def rmrsnipes(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Removes all snipes in a channel. Defaults to current channel."""
        channel = channel or ctx.channel

        num_deleted = await ReactionSnipe.delete_all_in(channel.id)

        if num_deleted > 0:
            await ctx.send(f"Deleted {num_deleted} snipes in {channel.mention}")
        else:
            await ctx.send(f"I couldn't find anything to delete in {channel.mention}")

    @tasks.loop(minutes=TTL_MINUTES)
    async def delete_snipe_db_purge(self):
        oldest_time = discord.utils.utcnow() - datetime.timedelta(minutes=TTL_MINUTES)
        oldest_timestamp = int(oldest_time.timestamp())

        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM reactionsnipe WHERE removed_at < ?", oldest_timestamp)
                await db.commit()

                deleted = cur.get_cursor().rowcount
                _logger.info("Performing periodic deletesnipe purge. %d reactionsnipes removed.", deleted)


async def setup(bot: commands.Bot):
    _logger.info("Loading cog ReactionSnipeCog")
    await bot.add_cog(ReactionSnipeCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog ReactionSnipeCog")
