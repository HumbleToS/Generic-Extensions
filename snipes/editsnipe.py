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
import typing
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
CREATE TABLE IF NOT EXISTS editsnipe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edited_at BIGINT NOT NULL,
    sender_id BIGINT NOT NULL,
    before_content TEXT NULL,
    after_content TEXT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL
)
"""


@dataclass(slots=True)
class EditSnipe:
    """Represents an edited Discord Messagee"""
    id: int
    edited_at: int
    sender_id: int
    before_content: str | None
    after_content: str | None
    guild_id: int
    channel_id: int

    @classmethod
    async def from_messages(cls, before: discord.Message, after: discord.Message, /) -> EditSnipe:
        """Creates a EditSnipe from a given `discord.Message`s

        Parameters
        ----------
        before : discord.Message
            The message before being edited
        after : discord.Message
            The message after being edited

        Returns
        -------
        Self
            The EditSnipe.
        """
        assert before.guild is not None
        assert after.guild is not None
        assert before.id == after.id

        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                edited_at = int(discord.utils.utcnow().timestamp())
                sender_id = after.author.id
                before_content = before.clean_content
                after_content = after.clean_content
                guild_id = after.guild.id
                channel_id = after.channel.id

                await cur.execute(f"""INSERT INTO editsnipe
                (edited_at, sender_id, before_content, after_content, guild_id, channel_id)
                VALUES (?, ?, ?, ?, ?, ?) RETURNING *""", edited_at, sender_id, before_content, after_content, guild_id, channel_id)
                res = await cur.fetchone()
                await db.commit()

                return cls(**res)

    @classmethod
    async def get_in_channel(cls, channel_id: int, /, *, offset: int = 0) -> EditSnipe | None:
        """Gets a EditSnipe in a given channel at a given offset.

        This is ordered by edit time.

        Parameters
        ----------
        channel_id : int
            The channel to retrieve from
        offset : int, optional
            The number of entries back to check, by default 0

        Returns
        -------
        Self | None
            The EditSnipe if found, else None.
        """
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM editsnipe WHERE channel_id = ? ORDER BY edited_at DESC LIMIT 1 OFFSET ?", channel_id, offset)
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
                await cur.execute("""DELETE FROM editsnipe
                WHERE channel_id = ? AND id IN
                 (SELECT id FROM editsnipe WHERE channel_id = ? ORDER BY edited_at DESC LIMIT 1 OFFSET ?)""", channel_id, channel_id, offset)
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
                await cur.execute("DELETE FROM editsnipe WHERE channel_id = ?", channel_id)
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
                await cur.execute("DELETE FROM editsnipe WHERE sender_id = ?", user_id)
                await db.commit()

                return cur.get_cursor().rowcount

    @property
    def timestamp(self) -> datetime.datetime:
        """Returns a UTC datetime representing time of deletion"""
        return datetime.datetime.fromtimestamp(self.edited_at, tz=datetime.timezone.utc)

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
        assert ctx.guild

        author = ctx.guild.get_member(self.sender_id) or await ctx.bot.fetch_member(self.sender_id)

        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=author, icon_url=author.display_avatar.url)
        embed.timestamp = self.timestamp

        embed.add_field(name="Before", value=self.before_content, inline=False)
        embed.add_field(name="After", value=self.after_content, inline=False)

        return embed


class EditSnipeCog(commands.Cog):
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
        num_deleted = await EditSnipe.clear_all_for_user(user.id)
        _logger.info("Processed editsnipe clear for %s, removed %d editsnipes.", str(user), num_deleted)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None: return
        if after.author.bot: return
        if await BotUser.is_opt_out(after.author.id): return

        _logger.debug("Processing message edit in channel with id %d", after.channel.id)
        await EditSnipe.from_messages(before, after)

    @commands.command()
    @commands.guild_only()
    async def esnipe(self, ctx: commands.Context, num_back: int = 0) -> None:
        """Snipes an edited message in current channel."""
        snipe = await EditSnipe.get_in_channel(ctx.channel.id, offset=num_back)

        if snipe:
            await ctx.send(embed=await snipe.embed(ctx))
        else:
            await ctx.send("No snipe found.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def rmesnipe(self, ctx: commands.Context, num_back: int = 0) -> None:
        """Removes an editsnipe in current channel."""
        assert isinstance(ctx.channel, discord.abc.GuildChannel)

        num_deleted = await EditSnipe.delete_one_in(ctx.channel.id, offset=num_back)

        if num_deleted > 0:
            await ctx.send(f"Deleted snipe at index {num_back} in {ctx.channel.mention}")
        else:
            await ctx.send(f"I didn't find anything to delete in {ctx.channel.mention} at index {num_back}")

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    async def rmesnipes(self, ctx: commands.Context, channel: discord.TextChannel | None = None):
        """Removes all editsnipes in a channel. Defaults to current channel."""
        chan = channel or ctx.message.channel

        assert isinstance(chan, discord.abc.GuildChannel)

        num_deleted = await EditSnipe.delete_all_in(chan.id)

        if num_deleted > 0:
            await ctx.send(f"Deleted {num_deleted} snipes in {chan.mention}")
        else:
            await ctx.send(f"I couldn't find anything to delete in {chan.mention}")

    @tasks.loop(minutes=TTL_MINUTES)
    async def delete_snipe_db_purge(self):
        oldest_time = discord.utils.utcnow() - datetime.timedelta(minutes=TTL_MINUTES)
        oldest_timestamp = int(oldest_time.timestamp())

        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM editsnipe WHERE edited_at < ?", oldest_timestamp)
                await db.commit()

                deleted = cur.get_cursor().rowcount
                _logger.info("Performing periodic editsnipe purge. %d editsnipes removed.", deleted)


async def setup(bot: commands.Bot):
    _logger.info("Loading cog EditSnipeCog")
    await bot.add_cog(EditSnipeCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog EditSnipeCog")
