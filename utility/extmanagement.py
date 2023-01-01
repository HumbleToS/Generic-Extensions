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

"""
TODOS: Refactor error handling?
"""
import io
import logging
import traceback

from discord.ext import commands

_logger = logging.getLogger(__name__)

class ExtManagement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def extensions(self, ctx: commands.Context) -> None:
        """Sends a list of the extensions the bot currently has loaded."""
        extensions = "\n".join([extension for extension in self.bot.extensions])
        await ctx.send(f"Currently loaded extensions:\n{extensions}")

    @commands.command(aliases=("rlext", ))
    @commands.is_owner()
    async def reloadextension(self, ctx: commands.Context, *, ext_name: str):
        """Reloads an extension that's loaded.

        Parameters
        -----------
        ext_name: str
            The extension name to reload.
        """
        _logger.info(f"Reloading extension from command {ext_name=}")
        try:
            await self.bot.reload_extension(ext_name)
            await ctx.send(f"{ext_name} reloaded successfully.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext_name} not found.")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{ext_name} is not loaded.")
        except commands.NoEntryPointError:
            await ctx.send(f"{ext_name} has no entry point.")
        except commands.ExtensionFailed as error:
            buff = io.StringIO()
            error = getattr(error, 'original', error)

            traceback.print_exception(type(error), error, error.__traceback__, file=buff)

            buff.seek(0) # Back to start
            paginator = commands.Paginator()
            for line in buff:
                paginator.add_line(line)
            await ctx.send(f"{ext_name} failed to load:")
            for page in paginator.pages:
                await ctx.send(page)

    @commands.command(aliases=("rlexts", ))
    @commands.is_owner()
    async def reloadallextensions(self, ctx: commands.Context, db_manager: bool=False) -> None:
        """Reloads all extensions that are currently loaded.

        Parameters
        -----------
        db_manager: bool
            Whether to reload the db_manager cog. Defaults to False.
        """
        _logger.info(f"Reloading all extensions from command {db_manager=}")
        extensions_list = [item for item in self.bot.extensions]
        output_str = ""
        for extension in extensions_list:
            if not db_manager:
                if "dbmanager" in extension:
                    continue
            try:
                await self.bot.reload_extension(extension)
                output_str += f"{extension} reloaded successfully.\n"
            except commands.ExtensionNotFound:
                output_str += f"{extension} not found.\n"
            except commands.ExtensionAlreadyLoaded:
                output_str += f"{extension} is already loaded.\n"
            except commands.NoEntryPointError:
                output_str += f"{extension} has no entry point.\n"
            except commands.ExtensionFailed as error:
                output_str += f"{extension} failed to load.\n"

                buff = io.StringIO()
                error = getattr(error, 'original', error)

                traceback.print_exception(type(error), error, error.__traceback__, file=buff)

                buff.seek(0) # Back to start
                paginator = commands.Paginator()
                for line in buff:
                    paginator.add_line(line)
                for page in paginator.pages:
                    await ctx.send(page)
        await ctx.send(output_str)

    @commands.command(aliases=("lext", ))
    @commands.is_owner()
    async def loadextension(self, ctx: commands.Context, *, ext_name: str) -> None:
        """Loads an extension.

        Parameters
        -----------
        ext_name: str
            The extension path to load.
        """
        _logger.info(f"Loading extension {ext_name} from command.")

        await ctx.send(f"Loading extension: {ext_name}")

        try:
            await self.bot.load_extension(ext_name)
            await ctx.send(f"{ext_name} loaded successfully.")
        except commands.ExtensionNotFound:
            await ctx.send(f"{ext_name} not found.")
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f"{ext_name} is already loaded.")
        except commands.NoEntryPointError:
            await ctx.send(f"{ext_name} has no entry point.")
        except commands.ExtensionFailed as error:
            await ctx.send(f"{ext_name} failed to load:")

            buff = io.StringIO()
            error = getattr(error, 'original', error)

            traceback.print_exception(type(error), error, error.__traceback__, file=buff)

            buff.seek(0) # Back to start
            paginator = commands.Paginator()
            for line in buff:
                paginator.add_line(line)
            for page in paginator.pages:
                await ctx.send(page)

    @commands.command(aliases=("ulext", ))
    @commands.is_owner()
    async def unloadextension(self, ctx: commands.Context, *, ext_name: str) -> None:
        """Unloads an extension from the bot

        Parameters
        -----------
        ext_name: str
            The extension path to unload.
        """
        _logger.info(f"Unloading extension {ext_name} from command.")

        await ctx.send(f"Unloading extension: {ext_name}")

        try:
            await self.bot.unload_extension(ext_name)
            await ctx.send(f"{ext_name} unloaded successfully.")

        except commands.ExtensionNotFound:
            await ctx.send(f"{ext_name} could not be found as a valid extension.")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"{ext_name} is not currently loaded.")


async def setup(bot: commands.Bot):
    _logger.info("Loading cog ExtManagement")
    await bot.add_cog(ExtManagement(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog ExtManagement")