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
INCOMPLETE

This module uses the following third party libs installed via pip: asqlite (https://github.com/Rapptz/asqlite)

This module uses persistent views. You will need to add those views back to your bot on startup
in it's setup_hook. For an example of how persistent views work, see:
https://github.com/Rapptz/discord.py/blob/master/examples/views/persistent.py
"""

from dataclasses import dataclass
import logging

import asqlite
import discord
from discord.ext import commands, tasks

from utils.converters import TimeConverter

DB_FILENAME = "giveaways.sqlite"

GIVEAWAY_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS giveaways (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL,
    started_by_user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    entry_message_id INTEGER NOT NULL,
    started_at INTEGER NOT NULL,
    ends_at INTEGER NOT NULL,
    ended INTEGER NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS giveawayentrants (
    user_id INTEGER NOT NULL,
    giveaway_id INTEGER NOT NULL,
    entered_at INTEGER NOT NULL,
    FOREIGN KEY(giveaway_id) REFERENCES giveaways(id),
    PRIMARY KEY(user_id, giveaway_id)
);
"""

_logger = logging.getLogger(__name__)

@dataclass(slots=True)
class Giveaway:
    id: int
    item: str
    started_by_user_id: int
    guild_id: int
    channel_id: int
    entry_message_id: int
    started_at: int # UTC TIMESTAMP
    duration_seconds: int

    @classmethod
    async def create(cls, *, item: str, user_id: int, guild_id: int, channel_id: int, entry_message_id: int, started_at: int | None, duration_seconds: int) -> Giveaway:
        pass

    @classmethod
    async def next_ending_or_none(cls) -> Giveaway | None:
        pass



@dataclass(slots=True)
class GiveawayEntrant:
    user_id: int
    giveaway_id: int
    entered_at: int # UTC TIMESTAMP


class GiveAwayEnterView(discord.ui.View):

    @discord.ui.button(label="Enter", style=discord.ButtonStyle.green, custom_id="giveaway-entry-view-enter-button")
    async def enter_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        assert interaction.message

        user_id = interaction.user.id
        message_id = interaction.message.id

        # Upsert user here


class GiveawayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        return await super().cog_load()

    async def cog_unload(self) -> None:
        return await super().cog_unload()

    @commands.group()
    async def giveaway(self, ctx: commands.Context) -> None:
        pass

    @giveaway.command()
    async def start(self, ctx: commands.Context, length: TimeConverter, *, what: str) -> None:
        pass

    @giveaway.command()
    async def stop(self, ctx: commands.Context, id: int) -> None:
        pass

    @giveaway.command()
    async def cancel(self, ctx: commands.Context, id: int) -> None:
        pass

    @tasks.loop()
    async def giveaway_loop(self) -> None:
        pass


async def setup(bot: commands.Bot):
    _logger.info("Loading cog GiveawayCog")
    await bot.add_cog(GiveawayCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog GiveawayCog")
