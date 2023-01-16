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
from __future__ import annotations

import re
from typing import Generic, TypeVar

from discord import Interaction, app_commands
from discord.ext import commands


ConverterReturn = TypeVar("ConverterReturn")

__all__ = ["TimeConverter", "CodeblockConverter"]

# TimeConverter taken from `?tag time converter` on discord.py. Thank you pikaninja.
TIME_REGEX = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
TIME_DICT = {"h": 3600, "s": 1, "m": 60, "d": 86400}


class _BaseConverter(
    app_commands.Transformer, commands.Converter, Generic[ConverterReturn]
):
    async def handle(
        self, ctx_or_interaction: commands.Context | Interaction, arg: str
    ) -> ConverterReturn:
        raise NotImplementedError(
            "Subclass this base converter and override the handle coro"
        )

    async def convert(self, ctx: commands.Context, arg: str) -> ConverterReturn:
        return await self.handle(ctx, arg)

    async def transform(self, inter: Interaction, arg: str) -> ConverterReturn:
        return await self.handle(inter, arg)


class CodeblockConverter(_BaseConverter):
    async def handle(self, ctx_or_interaction, arg: str) -> str:
        if arg.startswith("`"):
            arg = arg.removeprefix("```").removesuffix("```")
            arg = arg.removeprefix("py\n")

        return arg


class TimeConverter(_BaseConverter):
    async def handle(self, ctx_or_interaction, argument: str):
        matches = TIME_REGEX.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += TIME_DICT[k] * float(v)
            except KeyError:
                raise commands.BadArgument(
                    "{} is an invalid time-key! h/m/s/d are valid!".format(k)
                )
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        return time
