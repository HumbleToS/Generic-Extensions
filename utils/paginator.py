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
import traceback
import typing

import discord

DEFAULT_TIMEOUT = 180

_logger = logging.getLogger(__name__)

class ToPageModal(discord.ui.Modal, title="Go to page...t"):
    new_page = discord.ui.TextInput(label="Page", placeholder="What page are we going to?", min_length=1)

    def __init__(self, *, max_pages: typing.Optional[int]) -> None:
        super().__init__()
        if max_pages is not None:
            pages_str = str(max_pages)
            self.new_page.placeholder = f"Enter a number between 1 and {pages_str}"
            self.new_page.max_length = len(pages_str)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        self.stop()

class EmbedPaginatorView(discord.ui.View):
    """Wraps a list of embeds into a View with items to move between them."""
    def __init__(self, owner: discord.Member | discord.User, embeds: list[discord.Embed]) -> None:
        super().__init__(timeout=DEFAULT_TIMEOUT)
        assert len(embeds) > 0
        self.message: discord.Message | None = None # should be set when the paginator is sent.
        self.owner = owner
        self.embeds = embeds
        self.max_index = len(embeds) - 1 # List indecies
        self.current_index = 0

        self._update_buttons()

    async def on_timeout(self) -> None:
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
        if interaction.user.id == self.owner.id:
            return True
        await interaction.response.send_message(f"This paginator belongs to {self.owner.mention}.", ephemeral=True)
        return False

    def _update_buttons(self) -> None:
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
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_index], view=self)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.gray, disabled=True)
    async def to_first_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.current_index = 0
        await self.update(interaction)

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.green, disabled=True)
    async def back_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if self.current_index >= 1:
            self.current_index -= 1
        await self.update(interaction)

    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple, disabled=True)
    async def count_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        # Should never be called. Just defer in case it gets called.
        await interaction.response.defer()

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.green)
    async def fwd_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if self.current_index < self.max_index:
            self.current_index += 1
        await self.update(interaction)

    @discord.ui.button(emoji="⏭️", style= discord.ButtonStyle.gray)
    async def to_last_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.current_index = self.max_index
        await self.update(interaction)

    @discord.ui.button(label="Go To Page...", style=discord.ButtonStyle.blurple)
    async def goto_modal(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
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
            await modal.interaction.response.send_message(f'Expected an integer not {value!r}', ephemeral=True)
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
    async def stop_btn(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(view=None)
        self.stop()

    @property
    def initial(self) -> discord.Embed:
        return self.embeds[0]
