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

import discord
from discord import app_commands
from discord.ext import commands

from .errorlog import ErrorLog

_logger = logging.getLogger(__name__)

class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def cog_load(self) -> None:
        tree = self.bot.tree
        tree.on_error = self.on_app_command_error

    def cog_unload(self) -> None:
        tree = self.bot.tree
        tree.on_error = tree.__class__.on_error

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:

        if isinstance(error, app_commands.CommandOnCooldown):
            if interaction.response.is_done():
                await interaction.followup.send(f"A little too quick there, try again in {error.retry_after:,.1f} seconds.")
            else:
                await interaction.response.send_message(f"A little too quick there, try again in {error.retry_after:,.1f} seconds.")

        else:
            trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            errorlog = await ErrorLog.create(traceback=trace, item=f"Command: {interaction.command.name}")

            _logger.error("Ignoring exception in app command {}:".format(interaction.command))
            _logger.error(trace)

            try:
                if interaction.response.is_done():
                    msg = await interaction.followup.send(embed=errorlog.pub_embed, wait=True)
                    _logger.error(f"Notification message succesfully sent in {interaction.channel.id=} {msg.id=}")
                else:
                    # Interaction not responded.
                    await interaction.response.send_message(embed=errorlog.pub_embed)
                    _logger.error(f"Error notification message successfully sent as a response.")
            except (discord.Forbidden, discord.HTTPException):
                _logger.error(f"Could not send error notification in {interaction.channel.id=}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:

        # testing leaving this off
        # if hasattr(ctx.command, 'on_error'):
        #     return

        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound, )

        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f'{ctx.command} has been disabled.', ephemeral=True)

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f'{ctx.command} can not be used in Private Messages.', ephemeral=True)
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"A little too quick there. Try again in {error.retry_after:,.1f} seconds.", delete_after=4.0, ephemeral=True)

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f"You do not have permission to use that command.", ephemeral=True)

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You must have missed an argument ({error.param.name}), please try again.", ephemeral=True, delete_after=30.0)

        elif isinstance(error, commands.BotMissingPermissions):
            try:
                perm_strings = [perm.replace("_", " ").title() for perm in error.missing_permissions]
                await ctx.send(f"I am missing the permissions needed to run that command: {', '.join(perm_strings)}")
            except discord.Forbidden:
                _logger.info(f"Missing permissions {', '.join(perm_strings)} to run command '{ctx.command.qualified_name}' in channel_id={ctx.channel.id}")

        elif isinstance(error, commands.UserNotFound):
            await ctx.send(f"Could not find user {error.argument}.")

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"You provided an invalid argument.")

        elif isinstance(error, commands.BadLiteralArgument):
            await ctx.send(f"Invalid literal given, valid options: {' '.join(error.literals)}")

        elif isinstance(error, commands.RangeError):
            await ctx.send(f"Invalid value (**{error.value}**) given.")

        else:
            trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            errorlog = await ErrorLog.create(traceback=trace, item=f"Command: {ctx.command.name}")

            _logger.error("Ignoring exception in command {}:".format(ctx.command))
            _logger.error(trace)

            try:
                msg = await ctx.channel.send(embed=errorlog.pub_embed)
                _logger.error(f"Notification message succesfully sent in {ctx.channel.id=} {msg.id=}")
            except (discord.Forbidden, discord.HTTPException):
                _logger.error(f"Could not send error notification in {ctx.channel.id=}")


async def setup(bot):
    _logger.info("Loading cog ErrorHandler")
    await bot.add_cog(ErrorHandler(bot))

async def teardown(bot):
    _logger.info("Unloading cog ErrorHandler")