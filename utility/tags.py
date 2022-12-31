
from __future__ import annotations

from dataclasses import dataclass
import logging

import asqlite
from discord.ext import commands

DB_FILENAME = "tags.sqlite"

TAGS_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY NOT NULL AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    content TEXT NOT NULL
)
"""

@dataclass(slots=True)
class TagEntry:
    id: int
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

    @staticmethod
    async def delete(*, name: str, guild_id: int) -> int:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM tags WHERE name = ? AND guild_id = ?", name, guild_id)
                await db.commit()

                return cur.get_cursor().rowcount

    async def update(self, *, content: str) -> TagEntry:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("UPDATE tags SET content = ? WHERE name = ? AND guild_id = ? RETURNING *", content, self.name, self.guild_id)
                await db.commit()

                res = await cur.fetchone()

                return TagEntry(**res)

_logger = logging.getLogger(__name__)

class TagsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(invoke_without_subcommand=True)
    async def tag(self, ctx: commands.Context, *, query: str) -> None:
        pass

    @tag.command()
    async def make(self, ctx: commands.Context, name: str, *, content: str) -> None:
        pass

    @tag.command()
    async def delete(self, ctx: commands.Context, *, name: str) -> None:
        pass

    @tag.command()
    async def update(self, ctx: commands.Context, name: str, *, new_content: str) -> None:
        pass

    @tag.command()
    async def search(self, ctx: commands.Context, *, query: str) -> None:
        pass

async def setup(bot: commands.Bot):
    _logger.info("Loading cog TagsCog")
    await bot.add_cog(TagsCog(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog TagsCog")