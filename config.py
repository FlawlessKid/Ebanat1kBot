import os

# Токен бери у @BotFather. На Bothost.ru его обычно указывают
# в настройках проекта как переменную окружения BOT_TOKEN,
# либо можно просто вписать строкой сюда.
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER")

ADMIN_ID = 1146480839  # только этот id видит /admin

START_BALANCE = 1000
DAILY_REWARD = 500
DAILY_COOLDOWN_HOURS = 24

JACKPOT_SEED = 100                     # с чего джекпот стартует/пересобирается после выигрыша
SLOT_WIN_VALUES = {1, 22, 43, 64}      # значения анимации 🎰, дающие три одинаковых символа
SLOT_MEGA_VALUE = 64                   # 777 — топовая комбинация

QUOTE_REPLY_CHANCE = 0.03              # базовый шанс "воспоминания" фразы (0..1)
QUOTE_MIN_LEN = 4
QUOTE_MAX_LEN = 200
QUOTE_COOLDOWN_SECONDS = 30            # не чаще одного "воспоминания" за N секунд в чате

DB_PATH = "casino_bot.db"
