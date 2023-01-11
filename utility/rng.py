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
import logging
import random

import discord
from discord.ext import commands

_logger = logging.getLogger(__name__)

SUITS = ("Diamonds", "Hearts", "Spades", "Clubs")
RANKS = ("Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King")

POSSIBLE_DIE_FACES = (1, 2, 3, 4, 5, 6, 7, 12, 14, 16, 18, 20, 24, 30, 34, 48, 50, 60, 100, 120)
POSSIBLE_DIE_FACES_STR = " ".join(str(f) for f in POSSIBLE_DIE_FACES)

class RngCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=("choice",))
    async def choose(self, ctx: commands.Context, *choices: str) -> None:
        await ctx.send(random.choice(choices), allowed_mentions=discord.AllowedMentions.none())

    @commands.command()
    async def rand(self, ctx: commands.Context) -> None:
        """Random float in [0, 1)"""
        await  ctx.send(random.random())

    @commands.command()
    async def randint(self, ctx: commands.Context, minimum: int, maximum: int) -> None:
        """Random integer in [minimum, maximum]"""
        await ctx.send(random.randint(minimum, maximum))

    @commands.command()
    async def randcard(self, ctx: commands.Context) -> None:
        """Random playing card"""
        suit = random.choice(SUITS)
        rank = random.choice(RANKS)

        await ctx.send(f"{rank} of {suit}")

    @commands.command()
    async def dice(self, ctx: commands.Context, num_dice: int = 1, faces: int = 6) -> None:
        num_dice = max(min(num_dice, 20), 1)

        if not faces in POSSIBLE_DIE_FACES:
            await ctx.send(f"Invalid number of faces ({faces}) given.\nValid options are: {POSSIBLE_DIE_FACES_STR}")
            return

        res = [str(random.randint(1, faces)) for _ in range(num_dice)]
        res_str = "\n\t - ".join(res)

        await ctx.send(f"Result(s):\n\t - {res_str}")

async def setup(bot: commands.Bot):
    _logger.info("Loading cog RngCommandsCog")
    await bot.add_cog(RngCommandsCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog RngCommandsCog")