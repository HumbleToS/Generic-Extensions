
from __future__ import annotations

import logging

import discord
from discord.ext import commands

_logger = logging.getLogger(__name__)

class EmojiManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def createemoji(self, ctx: commands.Context, image: discord.Attachment, name: str) -> None:
        pass

    @commands.command()
    async def removeemoji(self, ctx: commands.Context, name: str) -> None:
        pass

    @commands.command()
    async def stealemoji(self, ctx: commands.Context, message_id: int) -> None:
        pass

async def setup(bot: commands.Bot):
    _logger.info("Loading cog EmojiManager")
    await bot.add_cog(EmojiManager(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog EmojiManager")