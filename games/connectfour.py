"""
MIT License

Copyright (c) 2022 Humble and rdrescher909

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

import itertools
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


# BRRRRT
class NumEmotes(Enum):
    """Represents unicode number plaques of each value."""

    ONE = "\U00000031\U0000fe0f\U000020e3"
    TWO = "\U00000032\U0000fe0f\U000020e3"
    THREE = "\U00000033\U0000fe0f\U000020e3"
    FOUR = "\U00000034\U0000fe0f\U000020e3"
    FIVE = "\U00000035\U0000fe0f\U000020e3"
    SIX = "\U00000036\U0000fe0f\U000020e3"
    SEVEN = "\U00000037\U0000fe0f\U000020e3"


class DiscType(Enum):
    """Represents unicode circles for player 1, player 2, and empty spaces (black)"""

    RED = "\U0001f534"
    BLACK = "\U000026ab"
    YELLOW = "\U0001f7e1"


@dataclass(slots=True, kw_only=True)
class Player:
    member: discord.Member
    emoji: DiscType


@dataclass(slots=True)
class DiscPiece:
    owner: Player


class ConnectFourBoard:
    def __init__(self) -> None:
        self.columns: int = 7
        self.rows: int = 6
        self._board: list[list[Optional[DiscPiece]]] = [[None for _ in range(self.columns)] for _ in range(self.rows)]

    def add_piece(self, column: int, piece: DiscPiece) -> Optional[int]:
        for row in reversed(range(self.rows)):
            if not self._board[row][column]:
                self._board[row][column] = piece
                return row
        return None

    @property
    def render(self) -> str:
        out = str()

        for column in range(self.rows):
            for row in range(self.columns):
                item = self._board[column][row]
                if item is not None:
                    out += f"{item.owner.emoji.value}"
                else:
                    out += f"{DiscType.BLACK.value}"
            out += "\n"
        out += "".join((num.value for num in NumEmotes))  # BLACK MAGIC

        return out

    def is_full(self) -> bool:
        return all(self._board[0])

    def is_win(self, piece: DiscType) -> bool:
        # Horizontal Win
        for row in range(self.rows):
            for col in range(self.columns - 3):
                if all(self._board[row][col + i] is not None and self._board[row][col + i].owner.emoji == piece for i in range(4)):  # type: ignore
                    return True

        # Vertical Win
        for row in range(self.rows - 3):
            for col in range(self.columns):
                if all(self._board[row + i][col] is not None and self._board[row + i][col].owner.emoji == piece for i in range(4)):  # type: ignore
                    return True

        # Diagonal Win
        for row in range(self.rows - 3):
            for col in range(self.columns - 3):
                if all(self._board[row + i][col + i] is not None and self._board[row + i][col + i].owner.emoji == piece for i in range(4)):  # type: ignore
                    return True
        for row in range(3, self.rows):
            for col in range(self.columns - 3):
                if all(self._board[row - i][col + i] is not None and self._board[row - i][col + i].owner.emoji == piece for i in range(4)):  # type: ignore
                    return True

        # If no win
        return False


class ConnectFourInput(discord.ui.View):
    message: discord.Message

    def __init__(self, player_one: discord.Member, player_two: discord.Member) -> None:
        super().__init__(timeout=60)
        self._player_one = Player(member=player_one, emoji=DiscType.RED)
        self._player_two = Player(member=player_two, emoji=DiscType.YELLOW)
        self.player_iterator = itertools.cycle((self._player_one, self._player_two))
        self.current_player = next(self.player_iterator)  # update after each move
        self._board = ConnectFourBoard()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        assert isinstance(interaction.user, discord.Member)

        if interaction.user == self.current_player.member:
            return True
        elif interaction.user != self.current_player.member and interaction.user in (
            self._player_one.member,
            self._player_two.member,
        ):
            await interaction.response.send_message(
                f"You cannot use this currently, it's {self.current_player.member.mention}'s turn.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(f"You are not a part of this game.", ephemeral=True)

        return False

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore
        await self.message.edit(
            content=f"Connect4: {self.current_player.member.mention} did not move in time so the game ended.",
            embed=None,
            view=None,
        )
        return await super().on_timeout()

    def get_base_embed(self) -> discord.Embed:
        base_embed = discord.Embed(
            title="Connect Four", description=f"{self._player_one.member.mention} vs {self._player_two.member.mention}\n"
        )
        base_embed.description += self._board.render  # type: ignore
        return base_embed

    async def update(self, interaction: discord.Interaction, /) -> None:
        base_embed = self.get_base_embed()
        assert base_embed.description is not None
        win = self._board.is_win(self.current_player.emoji)

        if win:
            base_embed.description += f""  # yes, I am this lazy
            await interaction.response.edit_message(
                content=f"{self.current_player.member.mention} has won.", embed=base_embed
            )
            await self.message.edit(view=None)  # that works
            self.stop()
        elif self._board.is_full():
            base_embed.description += "\n\nEnded in a tie."
            await interaction.response.edit_message(embed=base_embed)
            await self.message.edit(view=None)
            self.stop()
        else:
            next_player = next(self.player_iterator)
            self.current_player = next_player
            base_embed.description += f"\n\n{next_player.member.mention}'s move."
            await interaction.response.edit_message(embed=base_embed)

    @property
    def initial_embed(self) -> discord.Embed:
        embed = self.get_base_embed()
        embed.description += f"\n\n{self.current_player.member.mention}'s move."  # type: ignore
        return embed

    async def handle_move(self, interaction: discord.Interaction, *, players_move: int):
        self._board.add_piece(players_move, DiscPiece(self.current_player))
        await self.update(interaction)

    @discord.ui.button(emoji=NumEmotes.ONE.value)
    async def button_numero_uno(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, players_move=0)

    @discord.ui.button(emoji=NumEmotes.TWO.value)
    async def button_numero_dos(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, players_move=1)

    @discord.ui.button(emoji=NumEmotes.THREE.value)
    async def button_numero_tres(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, players_move=2)

    @discord.ui.button(emoji=NumEmotes.FOUR.value)
    async def button_numero_cuatro(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, players_move=3)

    @discord.ui.button(emoji=NumEmotes.FIVE.value)
    async def button_numero_cinco(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, players_move=4)

    @discord.ui.button(emoji=NumEmotes.SIX.value)
    async def button_numero_seis(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, players_move=5)

    @discord.ui.button(emoji=NumEmotes.SEVEN.value)
    async def button_numero_siete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, players_move=6)


class ConnectFour(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.describe(target="The user to play connect4 with")
    async def connect4(self, interaction: discord.Interaction, target: discord.Member):
        """Play connect4 with another user!"""
        assert isinstance(interaction.user, discord.Member)
        if target == interaction.user or target.bot:
            return await interaction.response.send_message("You cannot play against yourself or bots!", ephemeral=True)
        view = ConnectFourInput(player_one=interaction.user, player_two=target)
        embed = view.initial_embed
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(ConnectFour(bot))
