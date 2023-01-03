"""
Copyright 2020-present fretgfr

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
import asyncio
import contextlib
import logging
import math
import random
import traceback
import typing
from io import StringIO

import discord
from discord import embeds
from discord.ext import commands

_logger = logging.getLogger(__name__)

class ToPageModal(discord.ui.Modal, title="Go to page...t"):
    new_page = discord.ui.TextInput(label="Page", placeholder="What page are we going to?", min_length=1)

    def __init__(self, *, max_pages: typing.Optional[int]) -> None:
        super().__init__()
        _logger.debug(f"Creating new ToPageModal with {max_pages=}")
        if max_pages is not None:
            pages_str = str(max_pages)
            self.new_page.placeholder = f"Enter a number between 1 and {pages_str}"
            self.new_page.max_length = len(pages_str)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        _logger.debug(f"{self!r} on_submit processing.")
        self.interaction = interaction
        self.stop()

class CommandsPaginatorView(discord.ui.View):
    """Wraps a `commands.Paginator`'s pages into a View"""
    def __init__(self, owner: discord.Member | discord.User, paginator: commands.Paginator) -> None:
        super().__init__(timeout=300)
        assert len(paginator.pages) > 0
        self.message: discord.Message | None = None # should be set when the paginator is sent.
        self.owner = owner
        self.paginator = paginator
        self.max_index = len(paginator.pages) - 1 # List indecies
        self.current_index = 0

        self._update_state()

    async def on_timeout(self) -> None:
        _logger.debug(f"{self!r} timed out.")
        if self.message is not None:
            try:
                await self.message.edit(view=None)
            except discord.NotFound:
                pass

    async def on_error(self, interaction: discord.Interaction, error: Exception, _: discord.ui.Item) -> None:
        trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))

        _logger.error(f"Ignoring exception in view: {interaction.user.id=}")
        _logger.error(trace)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        _logger.debug(f"{self!r} received interaction from {interaction.user.id=}")
        if interaction.user.id == self.owner.id:
            return True
        await interaction.response.send_message(f"This paginator belongs to {self.owner.mention}.", ephemeral=True)
        return False

    def _update_state(self) -> None:
        _logger.debug(f"{self!r} _update called.")
        # Disable unusable buttons
        if self.current_index == self.max_index:
            self.fwd_btn.style = discord.ButtonStyle.grey
            self.fwd_btn.disabled = True
            self.to_last_btn.disabled = True
        else:
            self.fwd_btn.style = discord.ButtonStyle.green
            self.fwd_btn.disabled = False
            self.to_last_btn.disabled = False

        if self.current_index == 0:
            self.back_btn.style = discord.ButtonStyle.grey
            self.back_btn.disabled = True
            self.to_first_btn.disabled = True
        else:
            self.back_btn.style = discord.ButtonStyle.green
            self.back_btn.disabled = False
            self.to_first_btn.disabled = False

        self.count_btn.label = f"{self.current_index + 1}/{self.max_index + 1}" # Start at 1 instead of 0.

    async def update(self, interaction: discord.Interaction) -> None:
        _logger.debug(f"{self!r} update called.")
        self._update_state()
        await interaction.response.edit_message(content=self.paginator.pages[self.current_index], view=self)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.gray, disabled=True)
    async def to_first_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        _logger.debug(f"{self!r} to_first_btn clicked.")
        self.current_index = 0
        await self.update(interaction)

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.green, disabled=True)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        _logger.debug(f"{self!r} back_btn clicked.")
        if self.current_index >= 1:
            self.current_index -= 1
        await self.update(interaction)

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple, disabled=True)
    async def count_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        _logger.debug(f"{self!r} count_btn clicked.")
        # Should never be called. Just defer in case it gets called.
        await interaction.response.defer()

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.green)
    async def fwd_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        _logger.debug(f"{self!r} fwd_btn clicked.")
        if self.current_index < self.max_index:
            self.current_index += 1
        await self.update(interaction)

    @discord.ui.button(emoji="⏭️", style= discord.ButtonStyle.gray)
    async def to_last_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        _logger.debug(f"{self!r} to_last_btn clicked.")
        self.current_index = self.max_index
        await self.update(interaction)

    @discord.ui.button(label="Go To Page...", style=discord.ButtonStyle.blurple)
    async def goto_modal(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        _logger.debug(f"{self!r} goto_modal clicked.")
        if self.message is None:
            return

        modal = ToPageModal(max_pages=self.max_index + 1) # Their index is one higher than ours.
        await interaction.response.send_modal(modal)
        timed_out = await modal.wait()

        if timed_out:
            await interaction.followup.send('Took too long', ephemeral=True)
            return
        elif self.is_finished():
            await modal.interaction.response.send_message('Took too long', ephemeral=True)
            return

        value = str(modal.new_page.value)
        if not value.isdigit():
            await modal.interaction.response.send_message(f'Expected a number not {value!r}', ephemeral=True)
            return

        value = int(value)
        if not 0 < value <= self.max_index + 1:
            if not modal.interaction.response.is_done():
                error = modal.new_page.placeholder.replace("Enter", "Expected") # type: ignore
                await modal.interaction.response.send_message(error, ephemeral=True)
                return

        self.current_index = value - 1 # Our index is one lower than theirs
        await self.update(modal.interaction)

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(view=None)
        self.stop()

    @property
    def initial(self) -> str:
        return self.paginator.pages[0]

class PyTest(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=['ex', 'exec'])
    @commands.is_owner()
    async def py(self, ctx: commands.Context, *, code):
        """Runs arbitrary Python code.

        Parameters
        -----------
        code: str
            The code to run. Can be formatted without a codeblock, in a python codeblock, or in a bare codeblock.
        """
        mystdout = StringIO() #will hold the output of the code run

        async with ctx.channel.typing():
            if code.startswith("```python") and code.endswith("```"):
                code = code[10:-3]
            elif code.startswith("```py") and code.endswith("```"):
                code = code[5:-3]
            elif code.startswith("```") and code.endswith("```"):
                code = code[3:-3]
            else:
                code = code

            async def aexec(code, ctx):
                ldict = {}
                bot = self.bot

                exec(f'async def __ex(): ' + ''.join(f'\n {l}' for l in code.split('\n')), {"discord": discord, "random": random, "commands": commands, "embeds": embeds, "utils": discord.utils, "math": math, 'ctx': ctx, 'bot': bot, 'asyncio': asyncio, 'aio': asyncio}, ldict)
                return await ldict['__ex']() #await the created coro
            with contextlib.redirect_stdout(mystdout), contextlib.redirect_stderr(mystdout):
                await asyncio.wait_for(aexec(code, ctx), timeout=600) #Should time it out after 600 seconds
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        if mystdout.getvalue():
            paginator = commands.Paginator(max_size=400)
            for line in mystdout.getvalue().split("\n"):
                paginator.add_line(line)

            if len(paginator.pages) > 1: # paginate
                paginator_view = CommandsPaginatorView(ctx.author, paginator)
                initial_page = paginator_view.initial
                paginator_view.message = await ctx.send(initial_page, view=paginator_view)
            else: # no need to paginate
                await ctx.send(paginator.pages[0])

    @py.error
    async def err_handler(self, ctx, error):
        await ctx.send(f"```{error}```")
        await ctx.message.add_reaction("\N{CROSS MARK}")


async def setup(bot):
    _logger.info("Loading cog PyTest")
    await bot.add_cog(PyTest(bot))

async def teardown(_):
    _logger.info("Unloading cog PyTest")
