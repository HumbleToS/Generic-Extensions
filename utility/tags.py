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

"""
This module uses the following third party libs installed via pip: asqlite (https://github.com/Rapptz/asqlite)
"""

import logging
from dataclasses import dataclass

import asqlite
import discord
from discord.ext import commands

from utils.paginator import EmbedPaginatorView

ALLOWED_MENTIONS = discord.AllowedMentions.none()

DB_FILENAME = "tags.sqlite"

TAGS_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS tags (
    name TEXT NOT NULL,
    owner_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY(guild_id, name)
)
"""

_logger = logging.getLogger(__name__)

@dataclass(slots=True)
class TagEntry:
    name: str
    owner_id: int
    guild_id: int
    content: str

    @classmethod
    async def get_or_none(cls, *, name: str, guild_id: int) -> TagEntry | None:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM tags WHERE name = ? AND guild_id = ?", name, guild_id)
                res = await cur.fetchone()

                return cls(**res) if res is not None else None

    @classmethod
    async def create(cls, *, name: str, owner_id: int, guild_id: int, content: str) -> TagEntry | None:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                # TODO upsert?
                await cur.execute("""INSERT INTO tags (name, owner_id, guild_id, content) VALUES (?, ?, ?, ?)
                ON CONFLICT(name, guild_id) DO NOTHING RETURNING *""", name, owner_id, guild_id, content)

                res = await cur.fetchone()
                await db.commit()

                return cls(**res) if res is not None else None

    async def delete(self) -> int:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM tags WHERE name = ? AND guild_id = ?", self.name, self.guild_id)
                await db.commit()

                return cur.get_cursor().rowcount

    async def update(self, *, new_content: str = None) -> TagEntry:
        to_update_to = new_content or self.content
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("UPDATE tags SET content = ? WHERE name = ? AND guild_id = ? RETURNING *", to_update_to, self.name, self.guild_id)
                await db.commit()

                res = await cur.fetchone()

                return TagEntry(**res)


class TagsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        async with asqlite.connect(DB_FILENAME) as db:
            await db.execute(TAGS_SETUP_SQL)

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: commands.Context, *, name: str):
        """Gets a tag with given name

        Parameters
        ----------
        name : str
            The name of the tag to get.
        """
        tag = await TagEntry.get_or_none(name=name, guild_id=ctx.guild.id)

        if tag is not None:
            await ctx.send(tag.content, allowed_mentions=ALLOWED_MENTIONS)
        else:
            await ctx.send(f"Could not find tag with name `{name}`.")

    @tag.command(aliases=("make",))
    async def create(self, ctx: commands.Context, name: str, *, content: str) -> None:
        """Creates a tag with given name and content.

        Parameters
        ----------
        name : str
            The name of the tag to create.
        content : str
            The content of the tag to create.
        """
        tag = await TagEntry.create(name=name, owner_id=ctx.author.id, guild_id=ctx.guild.id, content=content)

        if tag is not None:
            await ctx.send(f"Tag with name `{name}` successfully created.")
        else:
            await ctx.send(f"Tag with name `{name}` already exists.")

    @tag.command(aliases=("rm",))
    async def delete(self, ctx: commands.Context, *, name: str) -> None:
        """Deletes a tag with given name. Works for tag owner and those with the Manage Messages server permission.

        Parameters
        ----------
        name : str
            The name of the tag to delete
        """
        original = await TagEntry.get_or_none(name=name, guild_id=ctx.guild.id)
        if not original:
            await ctx.send(f"Tag with name `{name}` not found.")
            return

        if original.owner_id != ctx.author.id and not ctx.author.guild_permissions.manage_messages:
            await ctx.send(f"You do not own the tag named `{name}`.")
            return

        removed = await original.delete()
        if removed:
            await ctx.send(f"Tag `{name}` deleted.")
        else:
            await ctx.send(f"Something went wrong while deleting `{name}`.")

    @tag.command(aliases=("edit",))
    async def update(self, ctx: commands.Context, name: str, *, new_content: str) -> None:
        """Updates a tag with given name and new content.

        Parameters
        ----------
        name : str
            The name of the tag to update.
        new_content : str
            The new content for the tag.
        """
        original = await TagEntry.get_or_none(name=name, guild_id=ctx.guild.id)
        if not original:
            await ctx.send(f"Tag with name `{name}` not found.")
            return

        if original.owner_id != ctx.author.id:
            await ctx.send(f"You do not own the tag named `{name}`.")
            return

        original.content = new_content
        updated = await original.update()

        await ctx.send(f"Tag with name {updated.name} content updated.")

    @tag.command()
    async def search(self, ctx: commands.Context, *, query: str) -> None:
        """Searches the tag list for tags with given query.

        Parameters
        ----------
        query : str
            The query to search for.
        """
        # TODO maybe make this use a paginator to display all results?
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT name FROM tags WHERE name LIKE ? and guild_id = ?", f"%{query}%", ctx.guild.id)

                results = await cur.fetchall()

                embeds = []

                for result in discord.utils.as_chunks(results, 20):
                    out = "\n".join(res['name'] for res in result)
                    embed = discord.Embed(color=discord.Color.blue(), description=out, title=query)
                    embeds.append(embed)

                if len(embeds) > 1:
                    paginator = EmbedPaginatorView(ctx.author, embeds)
                    paginator.message = await ctx.send(embed=paginator.initial, view=paginator)
                else:
                    await ctx.send(embed=embed)

                # IMPLEMENTATION WITHOUT PAGINATION:
                # if results:
                #     out = "\n".join(res['name'] for res in results[:20])
                #     if (num_results := len(results)) > 20:
                #         out += f"\n{num_results-20:,} other results."
                #     embed = discord.Embed(color=discord.Color.blue(), description=out, title=query)
                #     await ctx.send(embed=embed)
                # else:
                #     await ctx.send(f"No results found for `{query}`")

    @tag.command()
    async def list(self, ctx: commands.Context, *, member: discord.Member = None) -> None:
        """Lists the tags owned by a given user.

        Parameters
        ----------
        member : discord.Member
            The member to search for, defaults to member using the command.
        """
        # TODO maybe make this use a paginator to display all results?
        member = member or ctx.author

        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT name FROM tags WHERE owner_id = ? and guild_id = ?", member.id, ctx.guild.id)

                results = await cur.fetchall()

                embeds = []

                for result in discord.utils.as_chunks(results, 20):
                    out = "\n".join(res['name'] for res in result)
                    embed = discord.Embed(color=discord.Color.blue(), description=out, title=f"{member}'s Tags")
                    embeds.append(embed)

                if len(embeds) > 1:
                    paginator = EmbedPaginatorView(ctx.author, embeds)
                    paginator.message = await ctx.send(embed=paginator.initial, view=paginator)
                else:
                    await ctx.send(embed=embed)

                # IMPLEMENTATION WITHOUT PAGINATION:
                # if results:
                #     out = "\n".join(res['name'] for res in results[:20])
                #     if (num_results := len(results)) > 20:
                #         out += f"\n{num_results-20:,} other results."
                #     embed = discord.Embed(color=discord.Color.blue(), description=out, title=f"{member}'s Tags")
                #     await ctx.send(embed=embed)
                # else:
                #     await ctx.send(f"No results found for `{member}`")

    @tag.command()
    async def raw(self, ctx: commands.Context, *, name: str) -> None:
        tag = await TagEntry.get_or_none(name=name, guild_id=ctx.guild.id)

        if tag is not None:
            await ctx.send(discord.utils.escape_markdown(tag.content), allowed_mentions=ALLOWED_MENTIONS)
        else:
            await ctx.send(f"Could not find tag with name `{name}`.")


async def setup(bot: commands.Bot):
    _logger.info("Loading cog TagsCog")
    await bot.add_cog(TagsCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog TagsCog")