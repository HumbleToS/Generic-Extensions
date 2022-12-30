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

import asyncio
import datetime
import functools
import logging
import math
import platform
import time
import sys

import discord
from discord.utils import format_dt
from discord.ext import commands

"""
This module optionally uses the `psutil` pip package to display system information.
"""
try:
    import psutil
except ImportError:
    psutil = None

_logger = logging.getLogger(__name__)

def natural_size(size: int) -> str:
    unit = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')
    power = int(math.log(max(abs(size), 1), 1024))
    return f"{size/(1024**power):.2f} {unit[power]}"

class ApplicationInformationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _generate_embed(self, app_info: discord.AppInfo, /) -> discord.Embed:
        embed = discord.Embed(title="Application Info", color=discord.Color.blue())
        embed.add_field(name="Application ID", value=app_info.id, inline=False)
        embed.add_field(name="Application Name", value=app_info.name, inline=False)

        if app_info.team is not None:
            team = app_info.team
            embed.add_field(name="Owner", value=f"{team.owner.name} ({team.owner.mention})")
            embed.add_field(name="Team Members", value=len(team.members))
        else:
            embed.add_field(name="Owner", value=f"{app_info.owner.name} ({app_info.owner.mention})")

        embed.add_field(name="Public Bot?", value=f'{"Yes" if app_info.bot_public else "No"}')

        # Add default invite link if app has one.
        if app_info.bot_public:
            default_invite_link = discord.utils.oauth_url(self.bot.user.id, permissions=app_info.install_params.permissions) if app_info.install_params is not None else None
            if default_invite_link is not None:
                embed.add_field(name="Invite Link", value=f'[Default Invite Link]({default_invite_link} "Invite URL")')

        embed.add_field(name="Privacy Policy", value=f'[Privacy Policy]({app_info.privacy_policy_url} "Privacy Policy Link")' if app_info.privacy_policy_url is not None else "Doesn't have one", inline=False)
        embed.add_field(name="Terms of Service", value=f'[Terms of Service]({app_info.terms_of_service_url} "Privacy Policy Link")' if app_info.terms_of_service_url is not None else "Doesn't have one", inline=False)
        embed.add_field(name="Tags", value=", ".join(app_info.tags) if app_info.tags else "Doesn't have any.", inline=False)
        embed.add_field(name="Description", value=app_info.description if app_info.description else "Doesn't have one.", inline=False)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(name="Users", value=str(len(self.bot.users)))

        if hasattr(self.bot, "STARTED_AT"):
            embed.add_field(name="Bot Started", value=f"{format_dt(self.bot.STARTED_AT, 'F')} ({format_dt(self.bot.STARTED_AT, 'R')})", inline=False)

        embed.add_field(name="Running On", value=f"{platform.system()} {platform.release()} ({platform.machine()})", inline=False)
        embed.add_field(name="Python Version", value=f"{platform.python_implementation()} {platform.python_version()}")
        embed.add_field(name="discord.py Version", value=discord.__version__)
        embed.add_field(name="WS Latency", value=f"{self.bot.latency*1000:.3f}ms")

        if psutil is not None:
            proc = psutil.Process()
            mem = proc.memory_full_info()
            l_1, l_5, l_15 = psutil.getloadavg()

            if sys.platform == "darwin":
                pass

            if sys.platform.startswith("linux"):
                # Convert decimal formatted percentages to whole numbers.
                l_1 *= 100
                l_5 *= 100
                l_15 *= 100

            embed.add_field(name="Server Started", value=f"{format_dt(datetime.datetime.fromtimestamp(psutil.boot_time()).replace(tzinfo=datetime.timezone.utc), 'F')} ({format_dt(datetime.datetime.fromtimestamp(psutil.boot_time()).replace(tzinfo=datetime.timezone.utc), 'R')})", inline=False)
            embed.add_field(name="CPU Count", value=f"{psutil.cpu_count()} ({platform.processor()})")
            embed.add_field(name="Bot Using Memory", value=f"Physical: {natural_size(mem.rss)} || Virtual: {natural_size(mem.vms)}", inline=False)

            v_mem = psutil.virtual_memory()

            embed.add_field(name="Memory Info", value=f"Available: {natural_size(v_mem.available)} | Total: {natural_size(v_mem.total)}", inline=False)
            embed.add_field(name="Memory % Used", value=f"{v_mem.percent}%")
            embed.add_field(name="Thread Count", value=f"{proc.num_threads()}")
            embed.add_field(name="Load Averages", value=f"1m: {l_1:.3f}% 5m: {l_5:.3f}% 15m: {l_15:.3f}%", inline=False)

        return embed

    @commands.command(aliases=("info",))
    async def appinfo(self, ctx: commands.Context) -> None:
        """Sends application info."""
        start = time.perf_counter()
        app_info = await self.bot.application_info()

        if app_info is None:
            await ctx.send("Something went wrong...")
            return

        to_run = functools.partial(self._generate_embed, app_info)
        embed = await asyncio.to_thread(to_run)

        end = time.perf_counter()
        embed.set_footer(text=f"Command took {end-start:.2f}s")
        embed.timestamp = discord.utils.utcnow()

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    _logger.info("Loading cog ApplicationInformationCog")
    await bot.add_cog(ApplicationInformationCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog ApplicationInformationCog")