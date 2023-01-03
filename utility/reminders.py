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
This module uses the following third party libs installed via pip: asqlite (https://github.com/Rapptz/asqlite)
"""

from dataclasses import dataclass
import datetime
import logging
import re

import asqlite
import discord
from discord.ext import commands, tasks

DB_FILENAME = "reminders.sqlite"

REMINDER_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    timestamp BIGINT NOT NULL,
    body TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT FALSE
)
"""

_logger = logging.getLogger(__name__)

@dataclass(slots=True)
class ReminderEntry:
    id: int
    owner_id: int
    guild_id: int
    channel_id: int
    timestamp: int # UTC TIMESTAMP
    body: str
    completed: int

    @classmethod
    async def create(cls, *, owner_id: int, guild_id: int, channel_id: int, timestamp: int, body: str) -> ReminderEntry:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("""INSERT INTO reminders (owner_id, guild_id, channel_id, timestamp, body)
                VALUES (?, ?, ?, ?, ?) RETURNING *""", owner_id, guild_id, channel_id, timestamp, body)
                await db.commit()
                res = await cur.fetchone()

                return cls(**res)

    @classmethod
    async def get_or_none(cls, id: int, /) -> ReminderEntry | None:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM reminders WHERE id = ? AND completed = FALSE", id)
                res = await cur.fetchone()

                return cls(**res) if res is not None else None

    @classmethod
    async def get_next_or_none(cls) -> ReminderEntry | None:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM reminders WHERE completed = FALSE ORDER BY timestamp ASC LIMIT 1")
                res = await cur.fetchone()

                return cls(**res) if res is not None else None

    @staticmethod
    async def cancel(id: int, /) -> int:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("UPDATE reminders SET completed = TRUE WHERE id = ?", id)
                await db.commit()

                return cur.get_cursor().rowcount

    @staticmethod
    async def clear(*, guild_id: int, owner_id: int) -> int:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("UPDATE reminders SET completed = TRUE WHERE guild_id = ? AND owner_id = ?", guild_id, owner_id)
                await db.commit()

                return cur.get_cursor().rowcount

    async def mark_completed(self) -> ReminderEntry:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("UPDATE reminders SET completed = TRUE WHERE id = ?", self.id)
                await db.commit()

                if cur.get_cursor().rowcount > 0:
                    self.completed = 1

                return self


TIME_REGEX = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
TIME_DICT = {"h":3600, "s":1, "m":60, "d":86400}

class TimeConverter(commands.Converter):
    async def convert(self, _: commands.Context, argument: str):
        matches = TIME_REGEX.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += TIME_DICT[k]*float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        return time


class RemindersCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        async with asqlite.connect(DB_FILENAME) as db:
            await db.execute(REMINDER_SETUP_SQL)
        self.reminder_loop.start()

    async def cog_unload(self) -> None:
        self.reminder_loop.cancel()

    @tasks.loop()
    async def reminder_loop(self):
        next_reminder = await ReminderEntry.get_next_or_none()
        if next_reminder is None:
            self.reminder_loop.stop()
            return

        next_reminder_time_utc = datetime.datetime.fromtimestamp(next_reminder.timestamp, tz=datetime.timezone.utc)

        await discord.utils.sleep_until(next_reminder_time_utc)

        guild = self.bot.get_guild(next_reminder.guild_id)
        channel = self.bot.get_channel(next_reminder.channel_id)

        fulfilled = False

        if guild and channel:
            member = guild.get_member(next_reminder.owner_id) or await self.bot.fetch_user(next_reminder.owner_id)

            if member:
                await channel.send(f"{member.mention}: {next_reminder.body}")

                fulfilled = True

        if not fulfilled:
            _logger.info(f"Could not fulfil reminder in channel {next_reminder.channel_id}.")

        await next_reminder.mark_completed()

    @reminder_loop.before_loop
    async def before_reminder_loop(self):
        await self.bot.wait_until_ready()

    def start_restart_task(self) -> None:
        if self.reminder_loop.is_running():
            self.reminder_loop.restart()
        else:
            self.reminder_loop.start()

    # When discord comes out with date/time pickers, this
    # will be significantly easier to convert to a slash command.
    @commands.group(invoke_without_command=True, aliases=("remind", ))
    @commands.guild_only()
    async def reminder(self, ctx: commands.Context, when: TimeConverter, *, text: str = "Idk you never told me.") -> None:
        """Allows you to set reminders.

        Parameters
        ----------
        when : TimeConverter
            Short form offset time of when you need a reminder (e.x. 1h2m3s)
        text : str, optional
            The text for your reminder
        """
        now = discord.utils.utcnow()
        delta = datetime.timedelta(seconds=when)
        reminder_dt = now + delta

        owner_id = ctx.author.id
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        reminder_timestamp = reminder_dt.timestamp()

        new_reminder = await ReminderEntry.create(owner_id=owner_id, guild_id=guild_id, channel_id=channel_id, timestamp=reminder_timestamp, body=text)

        await ctx.reply(f"Reminder created (ID: {new_reminder.id}). I'll remind you at {discord.utils.format_dt(reminder_dt)}.")

        self.start_restart_task()

    @reminder.command()
    async def list(self, ctx: commands.Context) -> None:
        """Lists the reminders that you have set."""
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM reminders WHERE guild_id = ? AND owner_id = ? AND completed = FALSE ORDER BY timestamp ASC LIMIT 10", ctx.guild.id, ctx.author.id)

                results = await cur.fetchall()

                if results:
                    out = ""
                    for res in results:
                        id = res['id']
                        timestamp = datetime.datetime.fromtimestamp(res['timestamp'], tz=datetime.timezone.utc)

                        out += f"ID ({id}): {discord.utils.format_dt(timestamp)}\n"

                    embed = discord.Embed(description=out, title="Your Reminders", color=discord.Color.blue())

                    await ctx.reply(embed=embed)
                else:
                    await ctx.reply("You don't have any reminders set.")

    @reminder.command()
    async def cancel(self, ctx: commands.Context, id: int) -> None:
        """Cancels a reminder with given id.

        Parameters
        ----------
        id : int
            The id of the reminder to cancel.
        """
        reminder = await ReminderEntry.get_or_none(id)

        if reminder:
            if reminder.owner_id == ctx.author.id:
                await reminder.mark_completed()
                await ctx.reply(f"Reminder with id {id} cancelled.")
            else:
                await ctx.reply("You do not own that reminder.")
        else:
            await ctx.reply(f"No reminder with id {id} found.")

        self.start_restart_task()

    @reminder.command()
    async def clear(self, ctx: commands.Context) -> None:
        """Cancels all reminders you have set."""

        # TODO Probably add a confirm menu to this.
        num_removed = await ReminderEntry.clear(guild_id=ctx.guild.id, owner_id=ctx.author.id)

        await ctx.reply(f"Removed {num_removed} reminders of yours in this server.")

        self.start_restart_task()


async def setup(bot: commands.Bot):
    _logger.info("Loading cog RemindersCog")
    await bot.add_cog(RemindersCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog RemindersCog")
