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
import datetime
import io
import logging
from dataclasses import dataclass

import asqlite
import discord
from discord.ext import commands
from typing_extensions import Self

_logger = logging.getLogger(__name__)

DB_FILENAME = "errorlog.sqlite"

ERRORLOG_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS errorlog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unixtimestamp BIGINT NOT NULL,
    traceback TEXT NOT NULL,
    item TEXT NOT NULL
)
"""

@dataclass(slots=True)
class ErrorLog:
    id: int
    unixtimestamp: int
    traceback: str
    item: str

    @classmethod
    async def get_or_none(cls, id: int, /) -> Self | None:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM errorlog WHERE id = ?", id)

                res = await cur.fetchone()

                return cls(**res) if res is not None else None

    @classmethod
    async def create(cls, *, traceback: str, item: str) -> Self:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                now_utc = int(discord.utils.utcnow().timestamp())
                await cur.execute("INSERT INTO errorlog (unixtimestamp, traceback, item) VALUES (?, ?, ?) RETURNING *", now_utc, traceback, item)
                res = await cur.fetchone()
                await db.commit()

                return cls(**res)

    @classmethod
    async def delete(cls, id: int, /) -> int:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM errorlog WHERE id = ?", id)
                await db.commit()

                return cur.get_cursor().rowcount

    @classmethod
    async def get_most_recent(cls, num_to_get: int, /) -> list[Self] | None:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM errorlog ORDER BY id DESC LIMIT ?", num_to_get)

                logs = await cur.fetchall()

                return [cls(**res) for res in logs] if logs else None

    @property
    def timestamp(self) -> datetime.datetime:
        """Returns a UTC datetime representing time of deletion"""
        return datetime.datetime.fromtimestamp(self.unixtimestamp, tz=datetime.timezone.utc)

    @property
    def embed(self) -> discord.Embed:
        """Generates an Embed that represents this Error.

        Returns
        -------
        discord.Embed
            The generated Embed.
        """
        embed = discord.Embed(title=f"Error #{self.id}{f' (Item/Command: {self.item})' if self.item is not None else ''}", color=discord.Color.blue())
        embed.description = f"```{self.traceback[:5500]}```"
        embed.set_footer(text=f"Occurred On: {self.timestamp:%m-%d-%Y} at {self.timestamp:%I:%M:%M %p} UTC")

        return embed

    @property
    def pub_embed(self) -> discord.Embed:
        """Returns the public embed message for this error.

        Returns
        -------
        discord.Embed
            The generated Embed.
        """
        return discord.Embed(title=f"An unexpected error occured (ID: {self.id})", description=f"My developers are aware of the issue.\n\nIf you want to discuss this error with my developer, join the [support server](https://discord.gg/f64pfnqbJJ \"Support Server Invite URL\") and refer to the error by it's id. (ID: {self.id})", color=discord.Color.blue())

    @property
    def raw_text(self) -> str:
        """Returns the error in a raw text buffer."""
        output = (
            f"Error #{self.id}{f' (Item/Command: {self.item})' if self.item is not None else ''}\n"
            f"Occurred On: {self.timestamp:%m-%d-%Y} at {self.timestamp:%I:%M:%M %p} UTC\n"
            f"{self.traceback}\n"
        )
        return output

    @property
    def raw_bytes(self) -> io.BytesIO:
        """Returns the error as raw UTF-8 encoded bytes buffer."""
        output = io.BytesIO(self.raw_text.encode("UTF-8"))
        output.seek(0)

        return output


class ErrorLogCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        async with asqlite.connect(DB_FILENAME) as db:
            await db.execute(ERRORLOG_SETUP_SQL)

    @commands.command(aliases=('e', ))
    @commands.is_owner()
    async def error(self, ctx: commands.Context, error_id: int, raw: bool = False) -> None:
        """Sends an error from the database.

        Parameters
        ----------
        error_id : int
            The error id to send.
        raw : bool
            Whether to send the error in raw form, defaults to False
        """
        err = await ErrorLog.get_or_none(error_id)
        if not err:
            await ctx.send(f"I could not find an error with that id. (ID: {error_id})")
            return
        if raw:
            await ctx.send(file=discord.File(err.raw_bytes, filename=f"{err.id} raw.txt"))
        else:
            await ctx.send(embed=err.embed)

    @commands.command(aliases=('re',))
    @commands.is_owner()
    async def recenterrors(self, ctx: commands.Context) -> None:
        """Returns the 20 most recently logged errors."""
        errs = await ErrorLog.get_most_recent(20)
        embed = discord.Embed(color=discord.Color.blue(), description="")
        if errs:
            for err in errs:
                embed.description += f"{err.id:0>5}: (Item: {err.item}) {err.timestamp:%m-%d-%Y} at {err.timestamp:%I:%M:%M %p} UTC\n\n"
            await ctx.send(embed=embed)
        else:
            await ctx.send("No errors logged yet.")

async def setup(bot: commands.Bot):
    _logger.info("Loading cog ErrorLogCog")
    await bot.add_cog(ErrorLogCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog ErrorLogCog")