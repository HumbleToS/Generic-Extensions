import asyncio
import logging

import discord
from discord.ext import commands

from kickflip_steps import KICKFLIP_STEPS

_logger = logging.getLogger(__name__)

class Kickflip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.default, wait=False)
    async def kickflip(self, ctx: commands.Context) -> None:
        embed = discord.Embed(description=f"```{KICKFLIP_STEPS[0]}```")
        embed.set_footer(text="ASCII Art From https://ascii.co.uk/art/skateboard")
        msg = await ctx.send(embed=embed)

        for step in KICKFLIP_STEPS[1:]:
            await asyncio.sleep(.5)
            embed.description = f"```{step}```"
            await msg.edit(embed=embed)


async def setup(bot: commands.Bot):
    _logger.info("Loading cog Kickflip")
    await bot.add_cog(Kickflip(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog Kickflip")
