"""
This code created by combining multiple different items from other projects.

Licenses for these portions of code are included above their respective parts, but
may be slightly altered to ensure they work with the current discord.py version.

All code not covered by one of the licenses contained within is licensed under the following:

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
import collections
import logging
import typing

import discord
from discord.ext import commands

_logger = logging.getLogger(__name__)

"""
Codeblock converter license

MIT License

Copyright (c) 2021 Devon (Gorialis) R

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
class Codeblock(typing.NamedTuple):
    """
    Represents a parsed codeblock from codeblock_converter
    """

    language: typing.Optional[str]
    content: str


def codeblock_converter(argument: str) -> Codeblock:
    """
    A converter that strips codeblock markdown if it exists.
    Returns a namedtuple of (language, content).
    :attr:`Codeblock.language` is an empty string if no language was given with this codeblock.
    It is ``None`` if the input was not a complete codeblock.
    """
    if not argument.startswith('`'):
        return Codeblock(None, argument)

    # keep a small buffer of the last chars we've seen
    last: typing.Deque[str] = collections.deque(maxlen=3)
    backticks = 0
    in_language = False
    in_code = False
    language: typing.List[str] = []
    code: typing.List[str] = []

    for char in argument:
        if char == '`' and not in_code and not in_language:
            backticks += 1  # to help keep track of closing backticks
        if last and last[-1] == '`' and char != '`' or in_code and ''.join(last) != '`' * backticks:
            in_code = True
            code.append(char)
        if char == '\n':  # \n delimits language and code
            in_language = False
            in_code = True
        # we're not seeing a newline yet but we also passed the opening ```
        elif ''.join(last) == '`' * 3 and char != '`':
            in_language = True
            language.append(char)
        elif in_language:  # we're in the language after the first non-backtick character
            if char != '\n':
                language.append(char)

        last.append(char)

    if not code and not language:
        code[:] = last

    return Codeblock(''.join(language), ''.join(code[len(language):-backticks]))


"""
Ansi command and related utils license.


MIT License

Copyright (c) 2022 JeyyGit

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
class AnsiMaker(discord.ui.View):
    def __init__(self, ctx, text):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.msg = None
        self.text = text
        self.code = ''
        self.state = {
            'format': {
                'bold': False,
                'underline': False,
            },
            'color': None,
            'bgcolor': None
        }

    async def update(self, interaction: discord.Interaction, button: discord.Button | None = None, identifier: str | None = None):
        if identifier:
            for child in self.children:
                if child != button and child.label.startswith(identifier):
                    child.style = discord.ButtonStyle.primary

        ansis = ['0']

        state = self.state
        fmt = state['format']

        if fmt['bold'] and fmt['underline']:
            ansis.append('1')
            ansis.append('4')
        elif fmt['bold']:
            ansis.append('1')
        elif fmt['underline']:
            ansis.append('4')

        if state['color']:
            ansis.append(state['color'])
        if state['bgcolor']:
            ansis.append(state['bgcolor'])

        if any([fmt['bold'], fmt['underline'], state['color'], state['bgcolor']]):
            self.code = f"\u001b[{';'.join(ansis)}m"

            await interaction.response.edit_message(content=f'```ansi\n{self.code}{self.text}\u001b[0m\n```', view=self, allowed_mentions=discord.AllowedMentions.none())
        else:
            self.code = ''
            await interaction.response.edit_message(content=f'```ansi\n{self.code}{self.text}\u001b[0m\n```', view=self, allowed_mentions=discord.AllowedMentions.none())

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message('This is not your interaction!', ephemeral=True)
            return False

        return True

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f'\`\`\`ansi\n{self.code}{self.text}\u001b[0m\n\`\`\`')

    @discord.ui.button(label='Delete', style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

    @discord.ui.button(label='Bold', style=discord.ButtonStyle.primary)
    async def bolder(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['format']['bold']:
            self.state['format']['bold'] = False
            button.style = discord.ButtonStyle.primary
        else:
            self.state['format']['bold'] = True
            button.style = discord.ButtonStyle.danger

        await self.update(interaction)

    @discord.ui.button(label='Underline', style=discord.ButtonStyle.primary)
    async def underliner(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['format']['underline']:
            self.state['format']['underline'] = False
            button.style = discord.ButtonStyle.primary
        else:
            self.state['format']['underline'] = True
            button.style = discord.ButtonStyle.danger

        await self.update(interaction)

    @discord.ui.button(label='T Gray', style=discord.ButtonStyle.primary)
    async def t_gray(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['color'] == '30':
            self.state['color'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['color'] = '30'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'T')

    @discord.ui.button(label='T Red', style=discord.ButtonStyle.primary)
    async def t_red(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['color'] == '31':
            self.state['color'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['color'] = '31'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'T')

    @discord.ui.button(label='T Green', style=discord.ButtonStyle.primary)
    async def t_green(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['color'] == '32':
            self.state['color'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['color'] = '32'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'T')

    @discord.ui.button(label='T Yellow', style=discord.ButtonStyle.primary)
    async def t_yellow(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['color'] == '33':
            self.state['color'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['color'] = '33'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'T')

    @discord.ui.button(label='T Blue', style=discord.ButtonStyle.primary)
    async def t_blue(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['color'] == '34':
            self.state['color'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['color'] = '34'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'T')

    @discord.ui.button(label='T Pink', style=discord.ButtonStyle.primary)
    async def t_pink(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['color'] == '35':
            self.state['color'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['color'] = '35'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'T')

    @discord.ui.button(label='T Cyan', style=discord.ButtonStyle.primary)
    async def t_cyan(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['color'] == '36':
            self.state['color'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['color'] = '36'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'T')

    @discord.ui.button(label='T White', style=discord.ButtonStyle.primary)
    async def t_white(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['color'] == '37':
            self.state['color'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['color'] = '37'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'T')

    @discord.ui.button(label='BG D Blue', style=discord.ButtonStyle.primary)
    async def bg_d_blue(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['bgcolor'] == '40':
            self.state['bgcolor'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['bgcolor'] = '40'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'BG')

    @discord.ui.button(label='BG Orange', style=discord.ButtonStyle.primary)
    async def bg_orange(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['bgcolor'] == '41':
            self.state['bgcolor'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['bgcolor'] = '41'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'BG')

    @discord.ui.button(label='BG Gray 1', style=discord.ButtonStyle.primary)
    async def bg_gray_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['bgcolor'] == '42':
            self.state['bgcolor'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['bgcolor'] = '42'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'BG')

    @discord.ui.button(label='BG Gray 2', style=discord.ButtonStyle.primary)
    async def bg_gray_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['bgcolor'] == '43':
            self.state['bgcolor'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['bgcolor'] = '43'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'BG')

    @discord.ui.button(label='BG Gray 3', style=discord.ButtonStyle.primary)
    async def bg_gray_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['bgcolor'] == '44':
            self.state['bgcolor'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['bgcolor'] = '44'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'BG')

    @discord.ui.button(label='BG Gray 4', style=discord.ButtonStyle.primary)
    async def bg_gray_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['bgcolor'] == '46':
            self.state['bgcolor'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['bgcolor'] = '46'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'BG')

    @discord.ui.button(label='BG Indigo', style=discord.ButtonStyle.primary)
    async def bg_indigo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['bgcolor'] == '45':
            self.state['bgcolor'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['bgcolor'] = '45'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'BG')

    @discord.ui.button(label='BG White', style=discord.ButtonStyle.primary)
    async def bg_white(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state['bgcolor'] == '47':
            self.state['bgcolor'] = None
            button.style = discord.ButtonStyle.primary
        else:
            self.state['bgcolor'] = '47'
            button.style = discord.ButtonStyle.danger

        await self.update(interaction, button, 'BG')


class AnsiUtilityCmd(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    """
    License: See MIT License above for author JeyyGit
    """
    @commands.command(aliases=['ft', 'ansi'], hidden=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def format_text(self, ctx, *, text: codeblock_converter):
        """Colored text format"""
        content = text.content.strip('\n')
        if len(content) > 980:
            return await ctx.reply('Text must be under 980 characters.')
        view = AnsiMaker(ctx, content)
        view.msg = await ctx.reply(f'```ansi\n{content}\n```', view=view, allowed_mentions=discord.AllowedMentions.none())


async def setup(bot: commands.Bot):
    _logger.info("Loading cog AnsiUtilityCmd")
    await bot.add_cog(AnsiUtilityCmd(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog AnsiUtilityCmd")