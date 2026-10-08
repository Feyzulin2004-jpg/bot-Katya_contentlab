# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.config import ADMIN_IDS, PRICE_RUB

BTN_FREE = "🎁 Бесплатный промт"
BTN_INSIDE = "📚 Что внутри"
BTN_BUY = "💳 Забрать за {} ₽".format(PRICE_RUB)
BTN_EXAMPLES = "👀 Примеры"
BTN_SUB = "📦 Абонемент"
BTN_FAQ = "❓ Вопросы"
BTN_ASK = "💬 Поддержка"
BTN_STATS = "📊 Статистика"


def main_reply(user_id=None):
    rows = [
        [KeyboardButton(BTN_FREE), KeyboardButton(BTN_INSIDE)],
        [KeyboardButton(BTN_EXAMPLES), KeyboardButton(BTN_FAQ)],
        [KeyboardButton(BTN_ASK), KeyboardButton(BTN_STATS)] if user_id in ADMIN_IDS else [KeyboardButton(BTN_ASK)],
        [KeyboardButton(BTN_BUY)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def welcome_price():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💸 Получить промт для прайса", callback_data="get:price")],
            [InlineKeyboardButton("📱 Хочу промт для сторис", callback_data="get:stories")],
            [InlineKeyboardButton("🎠 Хочу промт для карусели", callback_data="get:carousel")],
            [InlineKeyboardButton("📚 Посмотреть полный сборник", callback_data="catalog")],
        ]
    )


def welcome_stories():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📱 Получить промт для сторис", callback_data="get:stories")],
            [InlineKeyboardButton("💸 Хочу промт для прайса", callback_data="get:price")],
            [InlineKeyboardButton("🎠 Хочу промт для карусели", callback_data="get:carousel")],
            [InlineKeyboardButton("📚 Посмотреть полный сборник", callback_data="catalog")],
        ]
    )


def welcome_carousel():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎠 Получить промт для карусели", callback_data="get:carousel")],
            [InlineKeyboardButton("💸 Хочу промт для прайса", callback_data="get:price")],
            [InlineKeyboardButton("📱 Хочу промт для сторис", callback_data="get:stories")],
            [InlineKeyboardButton("📚 Посмотреть полный сборник", callback_data="catalog")],
        ]
    )


def welcome_kit():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚 Посмотреть, что внутри сборника", callback_data="catalog")],
            [InlineKeyboardButton("💳 Забрать сборник за {} ₽".format(PRICE_RUB), callback_data="buy")],
            [InlineKeyboardButton("🎁 Забрать бесплатный промт", callback_data="choose_free")],
        ]
    )


_FREE_CHOICE = (
    ("price", "💸 Промт для прайса"),
    ("stories", "📱 Промт для сторис"),
    ("carousel", "🎠 Промт для карусели"),
)

_MORE_FREE = {
    "price": "🔥 Забрать промт для прайса",
    "stories": "🔥 Забрать промт для сторис",
    "carousel": "🔥 Забрать промт для карусели",
}


def welcome_generic(kinds=None):
    wanted = set(kinds) if kinds else None
    rows = [
        [InlineKeyboardButton(label, callback_data="get:{}".format(kind))]
        for kind, label in _FREE_CHOICE
        if wanted is None or kind in wanted
    ]
    rows.append([InlineKeyboardButton("📚 Посмотреть полный сборник", callback_data="catalog")])
    return InlineKeyboardMarkup(rows)


def after_prompt(remaining):
    rows = [
        [InlineKeyboardButton(_MORE_FREE[kind], callback_data="get:{}".format(kind))]
        for kind in remaining or []
        if kind in _MORE_FREE
    ]
    rows.append(
        [InlineKeyboardButton("📚 Посмотреть, что ещё есть в сборнике", callback_data="catalog")]
    )
    return InlineKeyboardMarkup(rows)


def warmup():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("👀 Хочу посмотреть ещё примеры", callback_data="proof")]]
    )


def proof():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📚 Посмотреть весь сборник", callback_data="catalog")]]
    )


def segment():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👩‍💻 Я SMM-специалист", callback_data="seg:smm")],
            [InlineKeyboardButton("💼 Я владелец бизнеса / эксперт", callback_data="seg:business")],
            [InlineKeyboardButton("💅 Я бьюти мастер", callback_data="seg:master")],
            [InlineKeyboardButton("📱 Я блогер", callback_data="seg:blog")],
        ]
    )


def buy(label=None):
    text = label or "💳 Хочу весь сборник"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="buy")]])


def inside_and_buy():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚 Что внутри сборника", callback_data="catalog")],
            [InlineKeyboardButton("💳 Купить за {}".format(PRICE_RUB), callback_data="buy")],
        ]
    )


def offer():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Забрать сборник за {} ₽".format(PRICE_RUB), callback_data="buy")],
            [InlineKeyboardButton("👀 Посмотреть, что внутри", callback_data="catalog")],
        ]
    )


def catalog():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Забрать сборник за {}".format(PRICE_RUB), callback_data="buy")],
            [InlineKeyboardButton("👀 Посмотреть примеры", callback_data="examples")],
        ]
    )


def examples_end():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔥 ХОЧУ ВЕСЬ СБОРНИК", callback_data="buy")],
            [InlineKeyboardButton("👀 ПОКАЗАТЬ ЕЩЁ ПРИМЕРЫ", callback_data="more_examples")],
        ]
    )


def checkout():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Оплатить {}".format(PRICE_RUB), callback_data="pay")],
            [InlineKeyboardButton("👀 Ещё раз посмотреть, что внутри", callback_data="catalog")],
        ]
    )


def positioning():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔥 Забрать все промты за {}".format(PRICE_RUB), callback_data="pay"
                )
            ]
        ]
    )


def take_all():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📚 Забрать все 20+ промтов", callback_data="buy")]]
    )


def faq_list():
    rows = [
        [InlineKeyboardButton("❓ Что я получу после оплаты?", callback_data="faq:after_pay")],
        [InlineKeyboardButton("❓ Что внутри канала?", callback_data="faq:inside")],
        [InlineKeyboardButton("❓ Можно посмотреть примеры?", callback_data="faq:examples")],
        [InlineKeyboardButton("❓ Как выглядит канал?", callback_data="faq:channel_look")],
        [InlineKeyboardButton("❓ Как работает доступ?", callback_data="faq:access")],
        [InlineKeyboardButton("❓ Подходят для моей ниши?", callback_data="faq:niche")],
        [InlineKeyboardButton("❓ Можно для клиентских проектов?", callback_data="faq:clients")],
        [InlineKeyboardButton("❓ Если результат слабый?", callback_data="faq:weak")],
        [InlineKeyboardButton("❓ ChatGPT выдаёт хороший результат?", callback_data="faq:quality")],
        [InlineKeyboardButton("❓ Нужен ли платный ChatGPT?", callback_data="faq:free_gpt")],
        [InlineKeyboardButton("❓ Можно с телефона?", callback_data="faq:phone")],
        [InlineKeyboardButton("❓ Как оплатить?", callback_data="faq:how_pay")],
        [InlineKeyboardButton("💳 Забрать сборник", callback_data="buy")],
    ]
    return InlineKeyboardMarkup(rows)


def results():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📊 Контент и стратегия", callback_data="res:content")],
            [InlineKeyboardButton("🎨 Визуал", callback_data="res:visual")],
            [InlineKeyboardButton("📸 Обработка фото", callback_data="res:photo")],
            [InlineKeyboardButton("💳 Забрать сборник", callback_data="buy")],
        ]
    )


def channel(url):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Перейти в канал", url=url)]])


def pay_url(url):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("💳 Оплатить {}".format(PRICE_RUB), url=url)]]
    )


def second_nudge():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📱 Получить второй промт", callback_data="second")]]
    )


def look_collection():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("👀 Посмотреть сборник", callback_data="catalog")]]
    )


def look_inside():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📚 Посмотреть, что внутри", callback_data="catalog")]]
    )


def take_kit():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Забрать сборник", callback_data="buy")],
            [InlineKeyboardButton("📚 Посмотреть список промтов", callback_data="catalog")],
        ]
    )


def drip(step):
    buy_label = "💳 Купить сборник за {}".format(PRICE_RUB)
    mapping = {
        1: [
            [InlineKeyboardButton("👀 ПОКАЗАТЬ", callback_data="drip:show1")],
            [InlineKeyboardButton(buy_label, callback_data="buy")],
        ],
        2: [
            [InlineKeyboardButton("📂 ПОСМОТРЕТЬ СБОРНИК", callback_data="catalog")],
            [InlineKeyboardButton(buy_label, callback_data="buy")],
        ],
        3: [
            [InlineKeyboardButton("🔥 ХОЧУ ПОСМОТРЕТЬ ВСЕ", callback_data="catalog")],
            [InlineKeyboardButton("💳 Купить за {}".format(PRICE_RUB), callback_data="buy")],
        ],
        4: [
            [InlineKeyboardButton("📚 ПОКАЗАТЬ ВЕСЬ СБОРНИК", callback_data="catalog")],
            [InlineKeyboardButton(buy_label, callback_data="buy")],
        ],
        5: [
            [InlineKeyboardButton("🎨 ПОКАЗАТЬ ВИЗУАЛЬНЫЕ ПРОМТЫ", callback_data="drip:visual")],
            [InlineKeyboardButton(buy_label, callback_data="buy")],
        ],
        6: [
            [InlineKeyboardButton("👀 ПОКАЗАТЬ, КАК ЭТО РАБОТАЕТ", callback_data="drip:text")],
            [InlineKeyboardButton(buy_label, callback_data="buy")],
        ],
        7: [
            [InlineKeyboardButton("🎁 ПОКАЗАТЬ БОНУСЫ", callback_data="drip:bonus")],
            [InlineKeyboardButton(buy_label, callback_data="buy")],
        ],
        8: [
            [InlineKeyboardButton("📂 ХОЧУ ПОСМОТРЕТЬ ЧТО ВНУТРИ", callback_data="catalog")],
            [InlineKeyboardButton("💳 КУПИТЬ ЗА {}".format(PRICE_RUB), callback_data="buy")],
        ],
        9: [
            [InlineKeyboardButton("🔥 ПОСМОТРЕТЬ ВСЕ 20+ ПРОМТОВ", callback_data="catalog")],
            [InlineKeyboardButton(buy_label, callback_data="buy")],
        ],
        10: [
            [InlineKeyboardButton("💚 ЗАБРАТЬ СБОРНИК за {}".format(PRICE_RUB), callback_data="buy")],
        ],
        11: [
            [InlineKeyboardButton("🔥 ЗАБРАТЬ за {}".format(PRICE_RUB), callback_data="buy")],
        ],
        12: [
            [InlineKeyboardButton("🔥 ПОСМОТРЕТЬ СБОРНИК", callback_data="catalog")],
            [InlineKeyboardButton(buy_label, callback_data="buy")],
        ],
        13: [
            [InlineKeyboardButton("💳 ЗАБРАТЬ СБОРНИК ЗА {}".format(PRICE_RUB), callback_data="buy")],
        ],
        14: [
            [InlineKeyboardButton("🔥 ХОЧУ ВЕСЬ СБОРНИК", callback_data="buy")],
            [InlineKeyboardButton("💳 Оплатить {}".format(PRICE_RUB), callback_data="pay")],
        ],
    }
    return InlineKeyboardMarkup(mapping.get(step, mapping[14]))
