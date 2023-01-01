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
import logging
import re

import discord
from discord.ext import commands

_logger = logging.getLogger(__name__)

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=('cu',))
    @commands.guild_only()
    @commands.cooldown(1, 5.0, commands.BucketType.user) # 1 per 5 seconds per user
    async def cleanup(self, ctx: commands.Context, amount: int=100):
        """Purges messages from and relating to the bot.

        Parameters
        ----------
        amount : int, optional
            The number of messages to check (1-100), defaults to 100.
        """
        amount = max(min(amount, 100), 1)

        async with ctx.typing():
            can_purge_author = ctx.channel.permissions_for(ctx.guild.me).manage_messages
            try:
                channel_prefixes = tuple(await self.bot.get_prefix(ctx.message))
                msgs = await ctx.channel.purge(limit=amount, check=lambda m: m.author == self.bot.user or (can_purge_author and m.author == ctx.author and m.content.startswith(channel_prefixes)))
                await ctx.send(f"Removed {len(msgs)} messages.", delete_after=10.0)

            except (discord.Forbidden, discord.HTTPException):
                await ctx.send("I couldn't process this request. Please check my permissions.")

    # This listener assumes that you only have a single prefix set.
    # IF you don't you will need to update this to display correctly.
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        if re.fullmatch(rf"<@!?{self.bot.user.id}>", msg.content):
            await msg.channel.send(f"My prefix is `{self.bot.command_prefix}`.")


async def setup(bot: commands.Bot):
    _logger.info("Loading cog Utility")
    await bot.add_cog(Utility(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog Utility")