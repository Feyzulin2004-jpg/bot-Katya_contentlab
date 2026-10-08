# -*- coding: utf-8 -*-
import logging
import re
import sys

from telegram.ext import (
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    PreCheckoutQueryHandler,
    Updater,
)

from bot.config import BOT_TOKEN, PRICE_RUB
from bot.db import init_db
from bot.handlers import (
    BTN_ASK,
    BTN_BUY,
    BTN_EXAMPLES,
    BTN_FAQ,
    BTN_FREE,
    BTN_INSIDE,
    BTN_STATS,
    BTN_SUB,
    cmd_channel,
    cmd_drip,
    cmd_grant,
    cmd_help,
    cmd_id,
    cmd_setchannel,
    cmd_start,
    cmd_stats,
    on_ask,
    on_buy_btn,
    on_callback,
    on_examples_btn,
    on_faq_btn,
    on_free,
    on_inside,
    on_my_chat_member,
    on_sub_btn,
    on_text,
    precheckout,
    successful_payment,
)
from bot.scheduler import JobLoop

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("bot")


def main():
    if not BOT_TOKEN or BOT_TOKEN.startswith("123456"):
        log.error("Укажи BOT_TOKEN в файле .env")
        sys.exit(1)
    init_db()
    updater = Updater(
        BOT_TOKEN,
        use_context=True,
        request_kwargs={
            "con_pool_size": 8,
            "connect_timeout": 30.0,
            "read_timeout": 180.0,
        },
    )
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("help", cmd_help))
    dp.add_handler(CommandHandler("stats", cmd_stats))
    dp.add_handler(CommandHandler("grant", cmd_grant))
    dp.add_handler(CommandHandler("drip", cmd_drip))
    dp.add_handler(CommandHandler("id", cmd_id))
    dp.add_handler(CommandHandler("channel", cmd_channel))
    dp.add_handler(CommandHandler("setchannel", cmd_setchannel))
    dp.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    def exact(text):
        return Filters.regex("^{}$".format(re.escape(text)))

    dp.add_handler(MessageHandler(exact(BTN_FREE), on_free))
    dp.add_handler(MessageHandler(exact(BTN_INSIDE), on_inside))
    dp.add_handler(MessageHandler(exact(BTN_BUY), on_buy_btn))
    dp.add_handler(MessageHandler(exact(BTN_EXAMPLES), on_examples_btn))
    dp.add_handler(MessageHandler(exact(BTN_SUB), on_sub_btn))
    dp.add_handler(MessageHandler(exact(BTN_FAQ), on_faq_btn))
    dp.add_handler(MessageHandler(exact(BTN_ASK), on_ask))
    dp.add_handler(MessageHandler(exact(BTN_STATS), cmd_stats))
    for old_text, handler in (
        ("🎁 Получить бесплатный промт", on_free),
        ("📚 Что внутри сборника", on_inside),
        ("💳 Забрать сборник за {} ₽".format(PRICE_RUB), on_buy_btn),
        ("💳 Забрать за 10 ₽", on_buy_btn),
        ("👀 Посмотреть примеры", on_examples_btn),
        ("📦 Абонемент", on_sub_btn),
        ("📦 Что с абонементом", on_sub_btn),
    ):
        dp.add_handler(MessageHandler(exact(old_text), handler))
    dp.add_handler(CallbackQueryHandler(on_callback))
    dp.add_handler(PreCheckoutQueryHandler(precheckout))
    dp.add_handler(MessageHandler(Filters.successful_payment, successful_payment))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, on_text))

    loop = JobLoop(updater.bot)
    loop.start()
    log.info("Бот запущен")
    updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=[
            "message",
            "callback_query",
            "pre_checkout_query",
            "my_chat_member",
        ],
    )
    updater.idle()
    loop.stop()


if __name__ == "__main__":
    main()
