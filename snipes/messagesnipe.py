
"""
This modules uses the following third party libs: asqlite, typing_extensions
"""


from dataclasses import dataclass
import datetime
import logging

import asqlite
import discord
from discord.ext import commands, tasks
from typing_extensions import Self

# If not using all snipe categories, you'll need to bring these items into this file,
# along with making sure the BotUser table is created and handling deleting opted out users data
# from the database (the custom event won't work unless you maintain that logic.)
from .snipescommon import DB_FILENAME
from .optout import BotUser


_logger = logging.getLogger(__name__)

# Maximum age will be TTL_MINUTES * 2
TTL_MINUTES = 5

SETUP_SQL = """
CREATE TABLE IF NOT EXISTS deletesnipe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deleted_at BIGINT NOT NULL,
    sender_id BIGINT NOT NULL,
    content TEXT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_reference_id BIGINT NULL
)
"""


@dataclass(slots=True)
class DeleteSnipe:
    """Represents a deleted Discord Message"""
    id: int
    deleted_at: int
    sender_id: int
    content: str | None
    guild_id: int
    channel_id: int
    message_reference_id: int | None

    @classmethod
    async def from_message(cls, message: discord.Message, /) -> Self:
        """Creates a DeleteSnipe from a given `discord.Message`.

        Parameters
        ----------
        message : discord.Message
            The message to create from

        Returns
        -------
        Self
            The generated DeleteSnipe.
        """
        assert message.guild is not None

        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                deleted_at = int(discord.utils.utcnow().timestamp())
                sender_id = message.author.id
                content = message.clean_content
                guild_id = message.guild.id
                channel_id = message.channel.id
                message_reference_id = message.reference.message_id if message.reference is not None else None

                await cur.execute(f"""INSERT INTO deletesnipe
                (deleted_at, sender_id, content, guild_id, channel_id, message_reference_id)
                VALUES (?, ?, ?, ?, ?, ?) RETURNING *""", deleted_at, sender_id, content, guild_id, channel_id, message_reference_id)
                res = await cur.fetchone()
                await db.commit()

                return cls(**res)

    @classmethod
    async def get_in_channel(cls, channel_id: int, /, *, offset: int = 0) -> Self | None:
        """Gets a DeleteSnipe in a given channel at a given offset.

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
            The found DeleteSnipe if found, else None.
        """
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM deletesnipe WHERE channel_id = ? ORDER BY deleted_at DESC LIMIT 1 OFFSET ?", channel_id, offset)
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
                await cur.execute("""DELETE FROM deletesnipe
                WHERE channel_id = ? AND id IN
                 (SELECT id FROM deletesnipe WHERE channel_id = ? ORDER BY deleted_at DESC LIMIT 1 OFFSET ?)""", channel_id, channel_id, offset)
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
                await cur.execute("DELETE FROM deletesnipe WHERE channel_id = ?", channel_id)
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
                await cur.execute("DELETE FROM deletesnipe WHERE sender_id = ?", user_id)
                await db.commit()

                return cur.get_cursor().rowcount

    @property
    def ref_jump_url(self) -> str | None:
        if self.message_reference_id is not None:
            return f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.message_reference_id}"
        return None

    @property
    def has_reference(self) -> bool:
        return self.message_reference_id is not None

    @property
    def timestamp(self) -> datetime.datetime:
        """Returns a UTC datetime representing time of deletion"""
        return datetime.datetime.fromtimestamp(self.deleted_at, tz=datetime.timezone.utc)

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
        author = ctx.guild.get_member(self.sender_id) or await ctx.bot.fetch_member(self.sender_id)

        embed = discord.Embed(description=self.content, color=discord.Color.blue())
        embed.set_author(name=author, icon_url=author.display_avatar.url)
        embed.timestamp = self.timestamp

        return embed


class MessageSnipeCog(commands.Cog):
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
        num_deleted = await DeleteSnipe.clear_all_for_user(user.id)
        _logger.info("Processed deletesnipe clear for %s, removed %d deletesnipes.", str(user), num_deleted)

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message) -> None:
        if msg.guild is None: return
        if msg.author.bot: return
        if await BotUser.is_opt_out(msg.author.id): return

        _logger.debug("Processing message delete in channel with id %d", msg.channel.id)
        await DeleteSnipe.from_message(msg)

    @commands.command()
    @commands.guild_only()
    async def snipe(self, ctx: commands.Context, num_back: int = 0) -> None:
        """Snipes a deleted message in current channel."""
        snipe = await DeleteSnipe.get_in_channel(ctx.channel.id, offset=num_back)

        if snipe:
            await ctx.send(embed=await snipe.embed(ctx))
        else:
            await ctx.send("No snipe found.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def rmsnipe(self, ctx: commands.Context, num_back: int = 0) -> None:
        """Removes a snipe in current channel."""
        num_deleted = await DeleteSnipe.delete_one_in(ctx.channel.id, offset=num_back)

        if num_deleted > 0:
            await ctx.send(f"Deleted snipe at index {num_back} in {ctx.channel.mention}")
        else:
            await ctx.send(f"I didn't find anything to delete in {ctx.channel.mention} at index {num_back}")

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    async def rmsnipes(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Removes all snipes in a channel. Defaults to current channel."""
        channel = channel or ctx.channel

        num_deleted = await DeleteSnipe.delete_all_in(channel.id)

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
                await cur.execute("DELETE FROM deletesnipe WHERE deleted_at < ?", oldest_timestamp)
                await db.commit()

                deleted = cur.get_cursor().rowcount
                _logger.info("Performing periodic deletesnipe purge. %d deletesnipes removed.", deleted)


async def setup(bot: commands.Bot):
    _logger.info("Loading cog MessageSnipeCog")
    await bot.add_cog(MessageSnipeCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog MessageSnipeCog")
