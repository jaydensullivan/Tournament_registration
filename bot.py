import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

import database as db
import bracket as br

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

logging.basicConfig(level=logging.INFO)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ---------- Registration FSM ----------

class Registration(StatesGroup):
    nickname = State()
    steam = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    existing = await db.get_player(message.from_user.id)
    if existing:
        await message.answer(
            f"ÐÑ ÑÐ¶Ðµ Ð·Ð°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð½Ñ ÐºÐ°Ðº <b>{existing['nickname']}</b>.\n"
            f"Steam: {existing['steam']}\n\n"
            "ÐÑÐ»Ð¸ Ð½ÑÐ¶Ð½Ð¾ Ð¸Ð·Ð¼ÐµÐ½Ð¸ÑÑ Ð´Ð°Ð½Ð½ÑÐµ â Ð½Ð°Ð¿Ð¸ÑÐ¸ÑÐµ /register Ð·Ð°Ð½Ð¾Ð²Ð¾.",
            parse_mode="HTML"
        )
        return
    await message.answer(
        "ð ÐÐ¾Ð±ÑÐ¾ Ð¿Ð¾Ð¶Ð°Ð»Ð¾Ð²Ð°ÑÑ Ð½Ð° ÑÐµÐ³Ð¸ÑÑÑÐ°ÑÐ¸Ñ SHOT CS:GO Cup!\n\n"
        "ÐÐ°Ðº Ð²Ð°Ñ Ð·Ð°Ð¿Ð¸ÑÐ°ÑÑ â ÑÐºÐ°Ð¶Ð¸ÑÐµ Ð²Ð°Ñ Ð¸Ð³ÑÐ¾Ð²Ð¾Ð¹ Ð½Ð¸Ðº:"
    )
    await state.set_state(Registration.nickname)


@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    await message.answer("Ð£ÐºÐ°Ð¶Ð¸ÑÐµ Ð²Ð°Ñ Ð¸Ð³ÑÐ¾Ð²Ð¾Ð¹ Ð½Ð¸Ðº:")
    await state.set_state(Registration.nickname)


@router.message(Registration.nickname)
async def reg_nickname(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text.strip())
    await message.answer("Ð¢ÐµÐ¿ÐµÑÑ Ð¿ÑÐ¸ÑÐ»Ð¸ÑÐµ ÑÑÑÐ»ÐºÑ Ð½Ð° Ð²Ð°Ñ Steam-Ð¿ÑÐ¾ÑÐ¸Ð»Ñ:")
    await state.set_state(Registration.steam)


@router.message(Registration.steam)
async def reg_steam(message: Message, state: FSMContext):
    data = await state.get_data()
    nickname = data["nickname"]
    steam = message.text.strip()

    await db.add_player(
        tg_id=message.from_user.id,
        username=message.from_user.username or "",
        nickname=nickname,
        steam=steam
    )
    await state.clear()
    await message.answer(
        f"â ÐÐ¾ÑÐ¾Ð²Ð¾! ÐÑ Ð·Ð°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð½Ñ ÐºÐ°Ðº <b>{nickname}</b>.\n"
        "ÐÑÐ³Ð°Ð½Ð¸Ð·Ð°ÑÐ¾ÑÑ Ð¾Ð±ÑÐµÐ´Ð¸Ð½ÑÑ ÑÑÐ°ÑÑÐ½Ð¸ÐºÐ¾Ð² Ð² ÐºÐ¾Ð¼Ð°Ð½Ð´Ñ Ð¿ÐµÑÐµÐ´ ÑÑÐ°ÑÑÐ¾Ð¼ ÑÑÑÐ½Ð¸ÑÐ°.",
        parse_mode="HTML"
    )


@router.message(Command("myinfo"))
async def cmd_myinfo(message: Message):
    p = await db.get_player(message.from_user.id)
    if not p:
        await message.answer("ÐÑ ÐµÑÑ Ð½Ðµ Ð·Ð°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð½Ñ. ÐÐ°Ð¶Ð¼Ð¸ÑÐµ /start")
        return
    await message.answer(f"ÐÐ¸Ðº: {p['nickname']}\nSteam: {p['steam']}")


# ---------- Admin: players & teams ----------

@router.message(Command("players"))
async def cmd_players(message: Message):
    if not is_admin(message.from_user.id):
        return
    players = await db.list_players()
    if not players:
        await message.answer("ÐÐ¾ÐºÐ° Ð½Ð¸ÐºÑÐ¾ Ð½Ðµ Ð·Ð°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð»ÑÑ.")
        return
    lines = [f"{p['tg_id']} â {p['nickname']} (@{p['username']})" for p in players]
    await message.answer("ÐÐ°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð½ÑÐµ Ð¸Ð³ÑÐ¾ÐºÐ¸:\n\n" + "\n".join(lines))


@router.message(Command("add_team"))
async def cmd_add_team(message: Message):
    """Usage: /add_team TeamName 111111 222222 333333 444444 555555"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "ÐÑÐ¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°Ð½Ð¸Ðµ:\n/add_team ÐÐ°Ð·Ð²Ð°Ð½Ð¸ÐµÐÐ¾Ð¼Ð°Ð½Ð´Ñ tg_id1 tg_id2 tg_id3 tg_id4 tg_id5\n\n"
            "tg_id ÑÑÐ°ÑÑÐ½Ð¸ÐºÐ¾Ð² ÑÐ¼Ð¾ÑÑÐ¸ÑÐµ Ð² /players"
        )
        return
    team_name = parts[1]
    try:
        tg_ids = [int(x) for x in parts[2:]]
    except ValueError:
        await message.answer("tg_id Ð´Ð¾Ð»Ð¶Ð½Ñ Ð±ÑÑÑ ÑÐ¸ÑÐ»Ð°Ð¼Ð¸. Ð¡Ð¼Ð¾ÑÑÐ¸ÑÐµ /players")
        return

    team_id = await db.create_team(team_name, tg_ids)
    await message.answer(f"â ÐÐ¾Ð¼Ð°Ð½Ð´Ð° Â«{team_name}Â» ÑÐ¾Ð·Ð´Ð°Ð½Ð° (ID {team_id}), Ð¸Ð³ÑÐ¾ÐºÐ¾Ð²: {len(tg_ids)}")


@router.message(Command("teams"))
async def cmd_teams(message: Message):
    if not is_admin(message.from_user.id):
        return
    teams = await db.list_teams()
    if not teams:
        await message.answer("ÐÐ¾Ð¼Ð°Ð½Ð´Ñ ÐµÑÑ Ð½Ðµ ÑÑÐ¾ÑÐ¼Ð¸ÑÐ¾Ð²Ð°Ð½Ñ. ÐÑÐ¿Ð¾Ð»ÑÐ·ÑÐ¹ÑÐµ /add_team")
        return
    lines = []
    for t in teams:
        members = ", ".join(m["nickname"] for m in t["members"])
        lines.append(f"#{t['id']} {t['name']}: {members}")
    await message.answer("\n".join(lines))


# ---------- Admin: bracket ----------

def match_keyboard(match_id: int, t1_id: int, t1_name: str, t2_id: int, t2_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"ð {t1_name}", callback_data=f"win:{match_id}:{t1_id}"),
        InlineKeyboardButton(text=f"ð {t2_name}", callback_data=f"win:{match_id}:{t2_id}")
    ]])


@router.message(Command("generate_bracket"))
async def cmd_generate_bracket(message: Message):
    if not is_admin(message.from_user.id):
        return
    teams = await db.list_teams()
    if len(teams) < 2:
        await message.answer("ÐÑÐ¶Ð½Ð¾ Ð¼Ð¸Ð½Ð¸Ð¼ÑÐ¼ 2 ÐºÐ¾Ð¼Ð°Ð½Ð´Ñ. Ð¡Ð½Ð°ÑÐ°Ð»Ð° Ð¸ÑÐ¿Ð¾Ð»ÑÐ·ÑÐ¹ÑÐµ /add_team")
        return

    team_dicts = [{"id": t["id"], "name": t["name"]} for t in teams]
    ready_match_ids = await br.generate_bracket(team_dicts)

    await message.answer(f"â Ð¡ÐµÑÐºÐ° ÑÐ³ÐµÐ½ÐµÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð° Ð´Ð»Ñ {len(teams)} ÐºÐ¾Ð¼Ð°Ð½Ð´.")

    names = {t["id"]: t["name"] for t in teams}
    for match_id in ready_match_ids:
        m = await db.get_match(match_id)
        t1_name = names.get(m["team1_id"], "TBD")
        t2_name = names.get(m["team2_id"], "TBD")
        await message.answer(
            f"âï¸ {t1_name} vs {t2_name}\nÐÑÐ±ÐµÑÐ¸ÑÐµ Ð¿Ð¾Ð±ÐµÐ´Ð¸ÑÐµÐ»Ñ:",
            reply_markup=match_keyboard(match_id, m["team1_id"], t1_name, m["team2_id"], t2_name)
        )


@router.message(Command("bracket"))
async def cmd_bracket(message: Message):
    teams = await db.list_teams()
    names = {t["id"]: t["name"] for t in teams}
    text = await br.render_bracket_text(names)
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("win:"))
async def cb_winner(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ð¢Ð¾Ð»ÑÐºÐ¾ Ð´Ð»Ñ Ð¾ÑÐ³Ð°Ð½Ð¸Ð·Ð°ÑÐ¾ÑÐ¾Ð²", show_alert=True)
        return

    _, match_id_str, winner_id_str = callback.data.split(":")
    match_id, winner_id = int(match_id_str), int(winner_id_str)

    winner_team = await db.get_team(winner_id)
    await callback.message.edit_text(
        f"{callback.message.text}\n\nð ÐÐ¾Ð±ÐµÐ´Ð¸ÑÐµÐ»Ñ: {winner_team['name']}"
    )
    await callback.answer()

    next_ready_id = await br.advance_winner(match_id, winner_id)
    if next_ready_id:
        m = await db.get_match(next_ready_id)
        t1 = await db.get_team(m["team1_id"])
        t2 = await db.get_team(m["team2_id"])
        await callback.message.answer(
            f"âï¸ {t1['name']} vs {t2['name']}\nÐÑÐ±ÐµÑÐ¸ÑÐµ Ð¿Ð¾Ð±ÐµÐ´Ð¸ÑÐµÐ»Ñ:",
            reply_markup=match_keyboard(next_ready_id, t1["id"], t1["name"], t2["id"], t2["name"])
        )
    else:
        m = await db.get_match(match_id)
        if not m["next_match_id"]:
            await callback.message.answer(f"ðð Ð¢ÑÑÐ½Ð¸Ñ Ð·Ð°Ð²ÐµÑÑÑÐ½! ÐÐ¾Ð±ÐµÐ´Ð¸ÑÐµÐ»Ñ: {winner_team['name']}")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN Ð½Ðµ Ð·Ð°Ð´Ð°Ð½. ÐÑÐ¾Ð²ÐµÑÑÑÐµ ÑÐ°Ð¹Ð» .env")

    await db.init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
