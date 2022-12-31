"""
Copyright 2022-present fretgfr

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT
OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
from __future__ import annotations

"""
This module emits a custom event: "on_optout_status_change" with the following parameters:
    - user (User | Member) -> The user that changed their status
    - new_status (bool) -> The user's new status.

This module uses the following third party libs installed via pip: asqlite (https://github.com/Rapptz/asqlite)
"""

from dataclasses import dataclass
import logging

import asqlite
from discord.ext import commands


from .snipescommon import DB_FILENAME

_logger = logging.getLogger(__name__)

BOTUSER_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS botuser (
    id BIGINT PRIMARY KEY,
    opted_out BOOLEAN
);
"""

# The Error and check below can be used above any of the commands
# that you want only people that aren't opted out to be able to use.
#
# Just add the decorator onto the command.
class NotOptedInError(commands.CommandError):
    """User is not opted in to snipes."""
    pass

def not_opted_out_only():
    """Returns True if a user is not opted out.

    Returns
    -------
    True
        The user is not opted out.

    Raises
    ------
    NotOptedInError
        The user is opted out.
    """
    async def predicate(ctx: commands.Context):
        is_opted_out = await BotUser.is_opted_out(ctx.author)
        if is_opted_out:
            raise NotOptedInError("User must be opted in to use this command.")
        return True
    return commands.check(predicate)


@dataclass(slots=True)
class BotUser:
    id: int
    opted_out: bool

    @classmethod
    async def create_or_update(cls, id: int, opted_out: bool) -> BotUser:
        """Creates or updates BotUser with given id and status

        Parameters
        ----------
        id : int
            The user id
        opted_out : bool
            The new status

        Returns
        -------
        Self
            The created or updated BotUser
        """
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("INSERT INTO botuser VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET opted_out = ? RETURNING *", id, opted_out, opted_out)
                res = await cur.fetchone()
                await db.commit()
                return cls(**res)

    @classmethod
    async def get(cls, id: int) -> BotUser | None:
        """Gets a BotUser with given id, if exists

        Parameters
        ----------
        id : int
            The id to search for

        Returns
        -------
        Self | None
            The BotUser if found, else None.
        """
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM botuser WHERE id = ?", id)
                res = await cur.fetchone()
                return cls(**res) if res is not None else None

    @classmethod
    async def delete(cls, id: int) -> int:
        """Deletes BotUser entry with given id.


        Parameters
        ----------
        id : int
            The id to delete

        Returns
        -------
        int
            The number of removed entries.
        """
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM botuser WHERE id = ?", id)
                await db.commit()

                return cur.get_cursor().rowcount

    @staticmethod
    async def is_opt_out(user_id: int, /) -> bool:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM botuser WHERE id = ?", user_id)
                res = await cur.fetchone()

                if res is not None:
                    return bool(res['opted_out'])
                return False

    @staticmethod
    async def toggle(user_id: int, /) -> bool:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("INSERT INTO botuser VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET opted_out = NOT opted_out RETURNING *", user_id, True)
                res = await cur.fetchone()
                await db.commit()
                return bool(res['opted_out'])


class OptOutCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        async with asqlite.connect(DB_FILENAME) as db:
            await db.execute(BOTUSER_SETUP_SQL)

    @commands.command()
    @commands.guild_only()
    async def optout(self, ctx: commands.Context) -> None:
        """Toggles your opt out status."""
        opted_out = await BotUser.toggle(ctx.author.id)

        if opted_out:
            self.bot.dispatch("optout_status_change", ctx.author, opted_out)
            await ctx.reply("You've been opted out.")
        else:
            await ctx.reply("You're opted back in.")


async def setup(bot: commands.Bot):
    _logger.info("Loading cog OptOutCog")
    await bot.add_cog(OptOutCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog OptOutCog")