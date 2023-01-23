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

"""
INCOMPLETE

Commands contained in this extension are slash commands, rather than prefix commands.
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

_logger = logging.getLogger(__name__)


class RoleManagerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    role = app_commands.Group(name="role")

    @role.command()
    async def give(self, interaction: discord.Interaction, role: discord.Role, member: discord.Member) -> None:
        pass

    @role.command()
    async def remove(self, interaction: discord.Interaction, role: discord.Role, member: discord.Member) -> None:
        pass

    @role.command()
    async def create(self, interaction: discord.Interaction, role_name: str) -> None: # Maybe more args?
        # Maybe interactive creation?
        pass

    @role.command()
    async def delete(self, interaction: discord.Interaction, role: discord.Role) -> None:
        pass

    @role.command()
    async def edit(self, interaction: discord.Interaction, role: discord.Role) -> None:
        # Maybe interactive editing?
        pass


async def setup(bot: commands.Bot):
    _logger.info("Loading cog RoleManagerCog")
    await bot.add_cog(RoleManagerCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog RoleManagerCog")
