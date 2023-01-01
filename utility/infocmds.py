
from __future__ import annotations

import logging

import discord
from discord.ext import commands

_logger = logging.getLogger(__name__)

class InformationCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def serverinfo(self, ctx: commands.Context) -> None:
        pass

    @commands.command()
    async def userinfo(self, ctx: commands.Context, user: discord.Member = None) -> None:
        user = user or ctx.author
        pass

    @commands.command()
    async def roleinfo(self, ctx: commands.Context, role: discord.Role = None) -> None:
        pass

async def setup(bot: commands.Bot):
    _logger.info("Loading cog InformationCommands")
    await bot.add_cog(InformationCommands(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog InformationCommands")