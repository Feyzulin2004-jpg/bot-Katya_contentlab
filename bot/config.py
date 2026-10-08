# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)


def _int_list(value):
    result = []
    for part in (value or "").split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return result


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = _int_list(os.getenv("ADMIN_IDS", ""))
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK", "").strip()
ACCESS_CHAT = os.getenv("ACCESS_CHAT", "").strip()
PAYMENT_URL = os.getenv("PAYMENT_URL", "").strip()
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip()
PRICE_RUB = int(os.getenv("PRICE_RUB", "999"))
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "").strip()
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "").strip()
YOOKASSA_RECEIPT_EMAIL = os.getenv("YOOKASSA_RECEIPT_EMAIL", "").strip()

DATA_DIR = os.path.join(BASE_DIR, "data")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
DB_PATH = os.path.join(DATA_DIR, "bot.db")

# Отложенные касания (секунды)
DELAY_WARMUP = 15 * 60              # ~15 мин после бесплатного промта
DELAY_SECOND_PROMPT_NUDGE = 25 * 60  # 25 мин, если молчит
DELAY_WHY_COLLECTION = 10 * 60 * 60  # 10 часов
DELAY_HOOK = 24 * 60 * 60            # 24 часа — ещё один бесплатный пример (боль → хук)
DELAY_CHECKOUT_1 = 3 * 60 * 60       # 3 часа после клика по оплате
DELAY_CHECKOUT_2 = 24 * 60 * 60      # сутки после клика по оплате
DELAY_FOLLOW = 5 * 60                # пауза между сообщениями в примерах и оплате
DELAY_DRIP = int(float(os.getenv("DRIP_HOURS", "24")) * 3600)
DRIP_TOTAL = 14

PRODUCT_NAME = "AI Content Kit"
PRODUCT_SHORT = "20+ готовых промтов для контента и визуала"
ACCESS_MONTHS = 12
