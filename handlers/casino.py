import asyncio
import random

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import database as db
import config

router = Router()


def parse_bet(raw: str, balance: int):
    try:
        bet = int(raw)
    except (ValueError, TypeError):
        return None, "Ставка должна быть целым числом."
    if bet <= 0:
        return None, "Ставка должна быть больше нуля."
    if bet > balance:
        return None, f"Недостаточно денег. Твой баланс: {balance}"
    return bet, None


@router.message(Command("slot"))
async def slot_cmd(message: Message):
    user = await db.get_or_create_user(
        message.from_user.id, message.from_user.username or message.from_user.first_name
    )
    args = message.text.split()[1:]
    if not args:
        await message.reply("Пример: /slot 100")
        return

    bet, error = parse_bet(args[0], user["balance"])
    if error:
        await message.reply(error)
        return

    await db.change_balance(message.from_user.id, -bet)
    jackpot = await db.get_jackpot()

    await message.reply(f"🎰 Ставка принята: {bet}\n💰 Джекпот на кону: {jackpot}\nКрутим барабаны...")
    dice_msg = await message.answer_dice(emoji="🎰")
    value = dice_msg.dice.value
    await asyncio.sleep(2.5)

    if value in config.SLOT_WIN_VALUES:
        win = jackpot
        new_balance = await db.change_balance(message.from_user.id, win)
        await db.set_jackpot(config.JACKPOT_SEED)
        mega = " 🔥 777, СУПЕР-ПРИЗ! 🔥" if value == config.SLOT_MEGA_VALUE else ""
        await message.answer(
            f"🎉 ВЫИГРЫШ!{mega}\nТы сорвал джекпот: +{win} монет!\n"
            f"Баланс: {new_balance}\nНовый джекпот: {config.JACKPOT_SEED}"
        )
    else:
        new_jackpot = jackpot + bet
        await db.set_jackpot(new_jackpot)
        new_balance = await db.get_balance(message.from_user.id)
        await message.answer(
            f"😢 Мимо. Ставка {bet} ушла в джекпот.\n"
            f"Баланс: {new_balance}\nДжекпот теперь: {new_jackpot}"
        )


@router.message(Command("dice"))
async def dice_cmd(message: Message):
    user = await db.get_or_create_user(
        message.from_user.id, message.from_user.username or message.from_user.first_name
    )
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply(
            "Пример: /dice 100 чет — ставка на чёт/нечет (x2)\n"
            "Или: /dice 100 5 — ставка на точное число 1-6 (x5)"
        )
        return

    bet, error = parse_bet(args[0], user["balance"])
    if error:
        await message.reply(error)
        return

    choice = args[1].lower()
    mode_exact = choice.isdigit() and 1 <= int(choice) <= 6
    mode_even = choice in ("чет", "чёт")
    mode_odd = choice in ("нечет", "нечёт")

    if not (mode_exact or mode_even or mode_odd):
        await message.reply("Второй аргумент: число 1-6 или 'чет'/'нечет'.")
        return

    await db.change_balance(message.from_user.id, -bet)
    dice_msg = await message.answer_dice(emoji="🎲")
    value = dice_msg.dice.value
    await asyncio.sleep(2.5)

    win = False
    multiplier = 0
    if mode_exact and int(choice) == value:
        win, multiplier = True, 5
    elif mode_even and value % 2 == 0:
        win, multiplier = True, 2
    elif mode_odd and value % 2 == 1:
        win, multiplier = True, 2

    if win:
        prize = bet * multiplier
        new_balance = await db.change_balance(message.from_user.id, prize)
        await message.answer(f"🎲 Выпало {value}! Выигрыш: {prize} монет.\nБаланс: {new_balance}")
    else:
        new_balance = await db.get_balance(message.from_user.id)
        await message.answer(f"🎲 Выпало {value}. Не повезло.\nБаланс: {new_balance}")


@router.message(Command("coin"))
async def coin_cmd(message: Message):
    user = await db.get_or_create_user(
        message.from_user.id, message.from_user.username or message.from_user.first_name
    )
    args = message.text.split()[1:]
    if len(args) < 2 or args[1].lower() not in ("орел", "орёл", "решка"):
        await message.reply("Пример: /coin 100 орел  (или решка)")
        return

    bet, error = parse_bet(args[0], user["balance"])
    if error:
        await message.reply(error)
        return

    choice = "орел" if args[1].lower() in ("орел", "орёл") else "решка"
    await db.change_balance(message.from_user.id, -bet)
    await message.reply(f"🪙 Подбрасываем монетку... ставка {bet} на «{choice}»")
    await asyncio.sleep(1.5)
    result = random.choice(["орел", "решка"])

    if result == choice:
        prize = bet * 2
        new_balance = await db.change_balance(message.from_user.id, prize)
        await message.answer(f"🪙 Выпал(а) {result}! Выигрыш: {prize} монет.\nБаланс: {new_balance}")
    else:
        new_balance = await db.get_balance(message.from_user.id)
        await message.answer(f"🪙 Выпал(а) {result}. Мимо.\nБаланс: {new_balance}")
