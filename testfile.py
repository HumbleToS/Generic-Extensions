from dataclasses import dataclass
from typing_extensions import Self

import asyncio
import asqlite

DB_FILENAME = "test.sqlite"

SETUP_SQL = """
CREATE TABLE IF NOT EXISTS deletesnipe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deleted_at BIGINT NOT NULL,
    sender_id BIGINT NOT NULL,
    content TEXT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_reference_id BIGINT NULL
);

CREATE TABLE IF NOT EXISTS botuser (
    id BIGINT PRIMARY KEY,
    opted_out BOOLEAN
);
"""



@dataclass
class BotUser:
    id: int
    opted_out: bool

    @classmethod
    async def create_or_update(cls, id: int, opted_out: bool) -> Self:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("INSERT INTO botuser VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET opted_out = ? RETURNING *", id, opted_out, opted_out)
                res = await cur.fetchone()
                await db.commit()
                return cls(**res)

    @classmethod
    async def get(cls, id: int) -> Self | None:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("SELECT * FROM botuser WHERE id = ?", id)
                res = await cur.fetchone()
                return cls(**res) if res is not None else None

    @classmethod
    async def delete(cls, id: int) -> None:
        async with asqlite.connect(DB_FILENAME) as db:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM botuser WHERE id = ?", id)
                await db.commit()


async def main():
    async with asqlite.connect(DB_FILENAME) as db:
        await db.executescript(SETUP_SQL)

    for i in range(50):
        bu = await BotUser.create_or_update(i, False if i % 2 == 0 else True)
        print(bu)

    bu = await BotUser.get(25)

    for i in range(50):
        await BotUser.delete(i)

    bu = await BotUser.get(100)

    print(bu)

asyncio.run(main())