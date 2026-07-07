import os
import aiosqlite
from datetime import datetime

DB_PATH = os.getenv("DT_PATH", "tournament.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                nickname TEXT,
                steam TEXT,
                registered_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                team_id INTEGER,
                tg_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round INTEGER,
                position INTEGER,
                team1_id INTEGER,
                team2_id INTEGER,
                winner_id INTEGER,
                next_match_id INTEGER,
                next_slot INTEGER,
                message_id INTEGER,
                chat_id INTEGER
            )
        """)
        await db.commit()


async def add_player(tg_id: int, username: str, nickname: str, steam: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO players (tg_id, username, nickname, steam, registered_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (tg_id, username, nickname, steam, datetime.utcnow().isoformat())
        )
        await db.commit()


async def get_player(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
        return await cur.fetchone()


async def list_players():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM players ORDER BY registered_at")
        return await cur.fetchall()


async def create_team(name: str, tg_ids: list[int]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO teams (name, created_at) VALUES (?, ?)",
            (name, datetime.utcnow().isoformat())
        )
        team_id = cur.lastrowid
        for tg_id in tg_ids:
            await db.execute(
                "INSERT INTO team_members (team_id, tg_id) VALUES (?, ?)",
                (team_id, tg_id)
            )
        await db.commit()
        return team_id


async def list_teams():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM teams ORDER BY id")
        teams = await cur.fetchall()
        result = []
        for t in teams:
            m = await db.execute(
                "SELECT p.nickname, p.tg_id FROM team_members tm "
                "JOIN players p ON p.tg_id = tm.tg_id WHERE tm.team_id = ?",
                (t["id"],)
            )
            members = await m.fetchall()
            result.append({"id": t["id"], "name": t["name"], "members": [dict(r) for r in members]})
        return result


async def clear_bracket():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM matches")
        await db.commit()


async def insert_matches(rows: list[dict]):
    """rows: list of dicts with round, position, team1_id, team2_id, winner_id, next_match_id, next_slot.
    Returns list of inserted ids in the same order."""
    ids = []
    async with aiosqlite.connect(DB_PATH) as db:
        for r in rows:
            cur = await db.execute(
                "INSERT INTO matches (round, position, team1_id, team2_id, winner_id, next_match_id, next_slot) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (r["round"], r["position"], r.get("team1_id"), r.get("team2_id"),
                 r.get("winner_id"), r.get("next_match_id"), r.get("next_slot"))
            )
            ids.append(cur.lastrowid)
        await db.commit()
    return ids


async def update_match(match_id: int, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [match_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE matches SET {cols} WHERE id = ?", vals)
        await db.commit()


async def get_match(match_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
        return await cur.fetchone()


async def all_matches():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM matches ORDER BY round, position")
        return await cur.fetchall()


async def get_team(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
        return await cur.fetchone()
