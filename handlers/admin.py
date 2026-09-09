from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import config

router = Router()


class AdminStates(StatesGroup):
    waiting_target_id = State()
    waiting_balance_delta = State()
    waiting_broadcast = State()
    waiting_chance = State()


def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID


def admin_menu() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
        [InlineKeyboardButton(text="🏆 Топ игроков", callback_data="adm:top")],
        [InlineKeyboardButton(text="💰 Изменить баланс", callback_data="adm:balance")],
        [InlineKeyboardButton(text="🎰 Сбросить джекпот", callback_data="adm:jackpot_reset")],
        [InlineKeyboardButton(text="💭 Вкл/выкл повторяшку", callback_data="adm:quotes_toggle")],
        [InlineKeyboardButton(text="🎚 Шанс повторяшки", callback_data="adm:set_chance")],
        [InlineKeyboardButton(text="🧹 Очистить фразы", callback_data="adm:clear_phrases")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🛠 Админ-панель", reply_markup=admin_menu())


@router.callback_query(F.data == "adm:stats")
async def cb_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    s = await db.stats()
    jackpot = await db.get_jackpot()
    await call.message.answer(
        f"📊 Статистика:\n"
        f"Игроков: {s['users_count']}\n"
        f"Суммарный баланс всех: {s['total_balance']}\n"
        f"Сохранённых фраз: {s['phrases_count']}\n"
        f"Текущий джекпот: {jackpot}"
    )
    await call.answer()


@router.callback_query(F.data == "adm:top")
async def cb_top(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    users = await db.top_users(15)
    lines = ["🏆 Топ игроков:"]
    for i, u in enumerate(users, start=1):
        name = u["username"] or str(u["user_id"])
        lines.append(f"{i}. {name} ({u['user_id']}) — {u['balance']}")
    await call.message.answer("\n".join(lines) if users else "Пока пусто.")
    await call.answer()


@router.callback_query(F.data == "adm:jackpot_reset")
async def cb_jackpot_reset(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await db.set_jackpot(config.JACKPOT_SEED)
    await call.message.answer(f"🎰 Джекпот сброшен до {config.JACKPOT_SEED}.")
    await call.answer("Готово")


@router.callback_query(F.data == "adm:quotes_toggle")
async def cb_quotes_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    current = await db.get_setting("quotes_enabled")
    new_val = "0" if current == "1" else "1"
    await db.set_setting("quotes_enabled", new_val)
    status = "включена ✅" if new_val == "1" else "выключена ❌"
    await call.message.answer(f"💭 Повторяшка теперь {status}.")
    await call.answer()


@router.callback_query(F.data == "adm:clear_phrases")
async def cb_clear_phrases(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await db.clear_phrases()
    await call.message.answer("🧹 База фраз очищена.")
    await call.answer("Готово")


@router.callback_query(F.data == "adm:balance")
async def cb_balance_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer("Введи ID пользователя, которому меняем баланс:")
    await state.set_state(AdminStates.waiting_target_id)
    await call.answer()


@router.message(AdminStates.waiting_target_id)
async def admin_get_target_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.reply("ID должен быть числом. Введи ещё раз:")
        return
    await state.update_data(target_id=int(message.text))
    await message.answer("Теперь введи сумму изменения (можно с минусом, например -500):")
    await state.set_state(AdminStates.waiting_balance_delta)


@router.message(AdminStates.waiting_balance_delta)
async def admin_get_delta(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        delta = int(message.text)
    except ValueError:
        await message.reply("Нужно целое число. Введи ещё раз:")
        return
    data = await state.get_data()
    target_id = data["target_id"]
    await db.get_or_create_user(target_id, str(target_id))
    new_balance = await db.change_balance(target_id, delta)
    await message.answer(f"✅ Баланс {target_id} изменён на {delta}. Теперь: {new_balance}")
    await state.clear()


@router.callback_query(F.data == "adm:set_chance")
async def cb_set_chance_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    current = await db.get_setting("quote_chance")
    await call.message.answer(f"Текущий шанс: {current}\nВведи новое значение от 0 до 1 (например 0.05):")
    await state.set_state(AdminStates.waiting_chance)
    await call.answer()


@router.message(AdminStates.waiting_chance)
async def admin_get_chance(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        value = float(message.text.replace(",", "."))
        if not (0 <= value <= 1):
            raise ValueError
    except ValueError:
        await message.reply("Нужно число от 0 до 1. Введи ещё раз:")
        return
    await db.set_setting("quote_chance", str(value))
    await message.answer(f"✅ Шанс повторяшки установлен: {value}")
    await state.clear()


@router.callback_query(F.data == "adm:broadcast")
async def cb_broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer("Введи текст рассылки (уйдёт всем, кто хоть раз писал боту):")
    await state.set_state(AdminStates.waiting_broadcast)
    await call.answer()


@router.message(AdminStates.waiting_broadcast)
async def admin_get_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    users = await db.top_users(100000)
    sent, failed = 0, 0
    for u in users:
        try:
            await message.bot.send_message(u["user_id"], f"📢 {message.text}")
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ Рассылка завершена. Успешно: {sent}, ошибок: {failed}")
    await state.clear()
