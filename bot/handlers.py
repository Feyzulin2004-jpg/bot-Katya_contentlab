# -*- coding: utf-8 -*-
import logging

from telegram import LabeledPrice

from bot import db, texts
from bot import keyboards as kb
from bot.keyboards import BTN_ASK, BTN_BUY, BTN_EXAMPLES, BTN_FAQ, BTN_FREE, BTN_INSIDE, BTN_STATS, BTN_SUB
from bot import tags as T
from bot.config import (
    ADMIN_IDS,
    CHANNEL_INVITE_LINK,
    DELAY_CHECKOUT_1,
    DELAY_CHECKOUT_2,
    DELAY_FOLLOW,
    PAYMENT_URL,
    PRICE_RUB,
    PRODUCT_NAME,
    PRODUCT_SHORT,
    PROVIDER_TOKEN,
)
from bot.funnel import (
    catch_pending_payment,
    give_prompt,
    grant_access,
    send_asset,
    send_media_folder,
    send_text,
    start_yookassa_pay,
)
from bot.drip import arm_silence_drip, handle_button as drip_button

log = logging.getLogger(__name__)


def note_action(user_id):
    user = db.get_user(user_id)
    if user and not user["paid"]:
        arm_silence_drip(user_id)
    if user and user.get("waiting_question"):
        db.set_fields(user_id, waiting_question=0)


def is_admin(user_id):
    return user_id in ADMIN_IDS


def cmd_start(update, context):
    user = update.effective_user
    payload = ""
    if context.args:
        payload = context.args[0].strip().lower()
    source_tag = T.START_PAYLOADS.get(payload)
    db.upsert_user(user.id, user.username, user.first_name, source_tag)
    if source_tag:
        db.add_tag(user.id, source_tag)
    note_action(user.id)
    catch_pending_payment(context.bot, user.id)
    if db.get_user(user.id)["paid"]:
        context.bot.send_message(
            user.id,
            texts.ALREADY_PAID.format(link=CHANNEL_INVITE_LINK or "канал"),
            reply_markup=kb.main_reply(user.id),
            disable_web_page_preview=True,
        )
        if CHANNEL_INVITE_LINK:
            send_text(
                context.bot,
                user.id,
                "Открыть канал 👇",
                reply_markup=kb.channel(CHANNEL_INVITE_LINK),
            )
        return
    send_source_welcome(context.bot, user.id, source_tag)
    context.bot.send_message(user.id, "Меню внизу экрана 👇", reply_markup=kb.main_reply(user.id))


def cmd_help(update, context):
    send_text(context.bot, update.effective_user.id, texts.FAQ_INTRO, reply_markup=kb.faq_list())


def send_source_welcome(bot, user_id, source):
    if source == T.SOURCE_PRICE:
        text, markup = texts.WELCOME_PRICE, kb.welcome_price()
    elif source == T.SOURCE_STORIES:
        text, markup = texts.WELCOME_STORIES, kb.welcome_stories()
    elif source == T.SOURCE_CAROUSEL:
        text, markup = texts.WELCOME_CAROUSEL, kb.welcome_carousel()
    elif source == T.SOURCE_KIT:
        text, markup = texts.WELCOME_KIT, kb.welcome_kit()
    else:
        text, markup = texts.WELCOME_GENERIC, kb.welcome_generic()
    send_text(bot, user_id, text, reply_markup=markup)
    if source == T.SOURCE_KIT:
        user = db.get_user(user_id)
        if user and not user.get("segment"):
            send_text(bot, user_id, texts.SEGMENT_ASK, reply_markup=kb.segment())


def on_free(update, context):
    user_id = update.effective_user.id
    db.upsert_user(user_id, update.effective_user.username, update.effective_user.first_name)
    note_action(user_id)
    user = db.get_user(user_id)
    source = (user or {}).get("source")
    if source == T.SOURCE_KIT:
        send_text(context.bot, user_id, texts.CHOOSE_FREE, reply_markup=kb.welcome_generic())
        return
    send_source_welcome(context.bot, user_id, source)


def on_inside(update, context):
    note_action(update.effective_user.id)
    show_catalog(context.bot, update.effective_user.id)


def on_buy_btn(update, context):
    note_action(update.effective_user.id)
    show_checkout(context.bot, update.effective_user.id)


def on_examples_btn(update, context):
    note_action(update.effective_user.id)
    show_examples(context.bot, update.effective_user.id)


def on_sub_btn(update, context):
    note_action(update.effective_user.id)
    send_text(context.bot, update.effective_user.id, texts.SUBSCRIPTION_INFO, reply_markup=kb.offer())


def on_faq_btn(update, context):
    note_action(update.effective_user.id)
    send_text(context.bot, update.effective_user.id, texts.FAQ_INTRO, reply_markup=kb.faq_list())


def on_ask(update, context):
    user_id = update.effective_user.id
    note_action(user_id)
    db.set_fields(user_id, waiting_question=1)
    send_text(context.bot, user_id, texts.ASK_QUESTION, reply_markup=kb.main_reply(user_id))


def on_text(update, context):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name)
    row = db.get_user(user.id)
    if row and row.get("waiting_question"):
        db.set_fields(user.id, waiting_question=0)
        send_text(context.bot, user.id, texts.QUESTION_SENT)
        text = texts.QUESTION_TO_ADMIN.format(
            name=user.full_name,
            username=user.username or "без_ника",
            uid=user.id,
            text=update.message.text,
        )
        for admin_id in ADMIN_IDS:
            send_text(context.bot, admin_id, text)
        if row and not row["paid"]:
            arm_silence_drip(user.id)
        return
    note_action(user.id)
    send_text(
        context.bot,
        user.id,
        "Выбери действие в меню ниже.",
        reply_markup=kb.main_reply(user.id),
    )


def on_callback(update, context):
    query = update.callback_query
    user = query.from_user
    data = query.data or ""
    try:
        query.answer()
    except Exception:
        pass
    db.upsert_user(user.id, user.username, user.first_name)
    note_action(user.id)
    bot = context.bot
    uid = user.id

    if data == "get:price":
        give_prompt(bot, uid, "price")
    elif data == "get:stories":
        give_prompt(bot, uid, "stories")
    elif data == "get:carousel":
        give_prompt(bot, uid, "carousel")
    elif data == "choose_free":
        send_text(bot, uid, texts.CHOOSE_FREE, reply_markup=kb.welcome_generic())
    elif data == "second":
        left = [k for k, tag in T.FREE_BY_KIND.items() if not db.has_tag(uid, tag)]
        if len(left) == 1:
            give_prompt(bot, uid, left[0])
        else:
            send_text(bot, uid, texts.CHOOSE_FREE, reply_markup=kb.welcome_generic(left or None))
    elif data == "catalog":
        show_catalog(bot, uid)
    elif data == "proof":
        show_proof(bot, uid)
    elif data.startswith("seg:"):
        try:
            query.message.delete()
        except Exception:
            pass
        show_segment(bot, uid, data.split(":", 1)[1])
    elif data == "examples":
        show_examples(bot, uid)
    elif data == "more_examples":
        show_more_examples(bot, uid)
    elif data == "buy":
        show_checkout(bot, uid)
    elif data == "pay":
        start_pay(bot, uid)
    elif data == "ask":
        db.set_fields(uid, waiting_question=1)
        send_text(bot, uid, texts.ASK_QUESTION, reply_markup=kb.main_reply(uid))
    elif data == "faq":
        send_text(bot, uid, texts.FAQ_INTRO, reply_markup=kb.faq_list())
    elif data.startswith("faq:"):
        key = data.split(":", 1)[1]
        answer = texts.FAQ.get(key)
        if answer:
            extra_kb = kb.results() if key in ("examples", "quality") else kb.offer()
            if key == "channel_look":
                send_asset(
                    bot,
                    uid,
                    "IMG_8422",
                    caption=answer + "\n\n" + texts.PRODUCT_LOOK,
                    reply_markup=kb.offer(),
                )
            else:
                send_text(bot, uid, answer, reply_markup=extra_kb)
            if key == "quality":
                send_media_folder(bot, uid, "proof/quality")
            if key == "examples":
                show_examples(bot, uid)
        else:
            send_text(bot, uid, texts.FAQ_INTRO, reply_markup=kb.faq_list())
    elif data.startswith("res:"):
        show_results(bot, uid, data.split(":", 1)[1])
    elif data == "results":
        send_text(bot, uid, texts.RESULTS_CHOOSE, reply_markup=kb.results())
    elif data.startswith("drip:"):
        result = drip_button(bot, uid, data.split(":", 1)[1])
        if result == "catalog":
            show_catalog(bot, uid)
        elif result == "visual":
            show_results(bot, uid, "visual")


def show_catalog(bot, uid):
    db.add_tag(uid, T.VIEWED_PRODUCT)
    send_asset(bot, uid, "IMG_8422")
    send_text(bot, uid, texts.CATALOG, reply_markup=kb.catalog())


def show_proof(bot, uid):
    send_asset(bot, uid, "IMG_8398")
    send_text(bot, uid, texts.PROOF_VALUE, reply_markup=kb.proof())


def show_segment(bot, uid, key):
    # Не тянем хвост от «примеров»: фото контент-плана не должно прилетать после сегмента.
    db.cancel_user_jobs(uid, ["examples_plan", "examples_outro", "examples_prompt", "examples_more"])
    tag = T.SEGMENT_MAP.get(key)
    if tag:
        db.add_tag(uid, tag)
        db.set_fields(uid, segment=key)
    if key == "smm":
        send_text(bot, uid, texts.SEGMENT_SMM)
        send_asset(bot, uid, "IMG_8398")
        send_text(bot, uid, texts.SEGMENT_SMM_PLAN)
        send_text(bot, uid, texts.SEGMENT_SMM_PAIN)
        send_media_folder(bot, uid, "proof/smm_stack")
        send_text(bot, uid, "Можно забрать всю библиотеку целиком.", reply_markup=kb.buy())
    elif key == "business":
        send_text(bot, uid, texts.SEGMENT_BUSINESS)
        send_text(bot, uid, texts.SEGMENT_BUSINESS_PLUS, reply_markup=kb.buy("💳 Посмотреть полный сборник"))
        send_media_folder(bot, uid, "proof/visual")
    elif key == "master":
        send_asset(bot, uid, "IMG_8420", caption=texts.SEGMENT_MASTER, reply_markup=kb.main_reply(uid))
        send_media_folder(bot, uid, "proof/before_after")
        send_text(
            bot,
            uid,
            "Что входит в сборник — по кнопке ниже.",
            reply_markup=kb.inside_and_buy(),
        )
    else:
        send_asset(bot, uid, "IMG_8420", caption=texts.SEGMENT_BLOG, reply_markup=kb.main_reply(uid))
        send_media_folder(bot, uid, "proof/blog")
        send_text(bot, uid, "Дальше можно посмотреть полный список.", reply_markup=kb.inside_and_buy())


def show_examples(bot, uid):
    send_asset(bot, uid, "IMG_8431", caption=texts.EXAMPLES_INTRO)
    db.cancel_user_jobs(uid, ["examples_plan", "examples_outro", "examples_prompt", "examples_more"])
    db.schedule_job(uid, "examples_more", 2 * 60, payload="0")


def show_more_examples(bot, uid):
    send_text(bot, uid, texts.MORE_EXAMPLES)
    send_text(bot, uid, texts.MORE_SMM)
    send_asset(bot, uid, "IMG_8398")
    send_media_folder(bot, uid, "proof/content_plan")
    send_text(bot, uid, texts.MORE_BUSINESS)
    send_media_folder(bot, uid, "proof/visual")
    send_text(bot, uid, texts.MORE_MASTER)
    send_asset(bot, uid, "IMG_8420")
    send_media_folder(bot, uid, "proof/before_after")
    send_text(bot, uid, texts.RESULTS_CHOOSE, reply_markup=kb.results())


def show_results(bot, uid, kind):
    from bot import media as md

    if kind == "content":
        send_asset(
            bot,
            uid,
            "IMG_8398",
            caption="Как выглядит готовый контент-план на 14 дней после работы с промтом",
        )
        send_asset(
            bot,
            uid,
            "IMG_0047",
            caption="Как выглядят анализ конкурентов и сегментация ЦА",
        )
        send_asset(
            bot,
            uid,
            "IMG_8422",
            caption="Как выглядит диагностика аккаунта после работы с промтом",
            reply_markup=kb.results(),
        )
        return
    if kind == "visual":
        md.send_stems(
            bot,
            uid,
            ["IMG_8443", "IMG_8281", "IMG_7713", "IMG_7566"],
            caption="Визуальный контент, созданный с помощью промтов: прайсы, сторис, посты и карусели",
        )
        return
    if kind == "photo":
        send_asset(
            bot,
            uid,
            "IMG_8420",
            caption="Обработка фото для мастера маникюра – несколько промтов и разные результаты",
            reply_markup=kb.results(),
        )
        return
    send_text(bot, uid, texts.RESULTS_CHOOSE, reply_markup=kb.results())


def show_checkout(bot, uid):
    db.add_tag(uid, T.VIEWED_PRODUCT)
    send_text(bot, uid, texts.CHECKOUT, reply_markup=kb.checkout())
    db.schedule_job(uid, "checkout_value", DELAY_FOLLOW)
    db.schedule_job(uid, "checkout_pos", DELAY_FOLLOW * 2)


def start_pay(bot, uid):
    user = db.get_user(uid)
    if user and user["paid"]:
        send_text(
            bot,
            uid,
            texts.ALREADY_PAID.format(link=CHANNEL_INVITE_LINK or "канал"),
            reply_markup=kb.channel(CHANNEL_INVITE_LINK) if CHANNEL_INVITE_LINK else None,
        )
        return
    db.add_tag(uid, T.CLICKED_PAYMENT)
    db.schedule_job(uid, "checkout_1", DELAY_CHECKOUT_1)
    db.schedule_job(uid, "checkout_2", DELAY_CHECKOUT_2)
    if start_yookassa_pay(bot, uid):
        return
    if PROVIDER_TOKEN:
        try:
            bot.send_invoice(
                chat_id=uid,
                title=PRODUCT_NAME,
                description=PRODUCT_SHORT,
                payload="kit_{}".format(uid),
                provider_token=PROVIDER_TOKEN,
                currency="RUB",
                prices=[LabeledPrice(PRODUCT_NAME, PRICE_RUB * 100)],
            )
            return
        except Exception:
            log.exception("Invoice failed")
    if PAYMENT_URL:
        send_text(
            bot,
            uid,
            texts.PAY_LINK.format(price="{} ₽".format(PRICE_RUB), url=PAYMENT_URL),
        )
        return
    send_text(bot, uid, texts.NO_PAY_SETUP)


def precheckout(update, context):
    query = update.pre_checkout_query
    query.answer(ok=True)


def successful_payment(update, context):
    grant_access(context.bot, update.effective_user.id)


def cmd_stats(update, context):
    if not is_admin(update.effective_user.id):
        return
    s = db.stats()
    links = (
        ("source_price", "Прайс"),
        ("source_stories", "Сторис"),
        ("source_carousel", "Карусель"),
        ("source_kit", "Сборник"),
        ("", "Без ссылки"),
    )
    segments = (
        ("smm", "SMM"),
        ("business", "Бизнес"),
        ("master", "Бьюти-мастер"),
        ("blog", "Блогер"),
    )
    lines = [
        "Статистика",
        "",
        "Всего людей: {}".format(s["total"]),
        "Оплатили: {}".format(s["paid"]),
        "",
        "Перешли по ссылке",
    ]
    for key, title in links:
        lines.append("{}: {}".format(title, s["sources"].get(key, 0)))
    lines.append("")
    lines.append("Оплатили по ссылке")
    for key, title in links:
        lines.append("{}: {}".format(title, s["paid_sources"].get(key, 0)))
    lines.append("")
    lines.append("Кто они")
    for key, title in segments:
        lines.append("{}: {}".format(title, s["segments"].get(key, 0)))
    send_text(context.bot, update.effective_user.id, "\n".join(lines))


def cmd_grant(update, context):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        send_text(context.bot, update.effective_user.id, "Формат: /grant telegram_id")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        send_text(context.bot, update.effective_user.id, "Нужен числовой id.")
        return
    db.upsert_user(uid)
    grant_access(context.bot, uid)
    send_text(context.bot, update.effective_user.id, "Доступ выдан {}".format(uid))


def cmd_id(update, context):
    send_text(context.bot, update.effective_user.id, "Твой Telegram ID: {}".format(update.effective_user.id))


def _bind_access_chat(bot, chat):
    db.set_setting("access_chat_id", str(chat.id))
    db.set_setting("access_chat_title", chat.title or "")
    kind = {"channel": "канал", "supergroup": "группу", "group": "группу"}.get(chat.type, chat.type)
    invite_ok = True
    try:
        bot.create_chat_invite_link(chat_id=chat.id, member_limit=1)
    except Exception as exc:
        invite_ok = False
        log.warning("Invite check failed for %s: %s", chat.id, exc)
        err = str(exc)
    text = "Для выдачи доступа привязала {}: «{}»\nID: {}".format(
        kind, chat.title or "без названия", chat.id
    )
    if not invite_ok:
        text += (
            "\n\nTelegram отказал в создании ссылки: {}\n"
            "Если бот только что добавлен — подожди минуту и напиши /setchannel ещё раз."
        ).format(err)
    return text


def cmd_channel(update, context):
    if not is_admin(update.effective_user.id):
        return
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup", "channel"):
        text = _bind_access_chat(context.bot, chat)
        send_text(context.bot, update.effective_user.id, text)
        if chat.id != update.effective_user.id:
            try:
                context.bot.send_message(chat.id, "Этот чат привязан для выдачи доступа после оплаты.")
            except Exception:
                pass
        return
    cmd_setchannel(update, context)


def cmd_setchannel(update, context):
    if not is_admin(update.effective_user.id):
        return
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup", "channel"):
        send_text(context.bot, update.effective_user.id, _bind_access_chat(context.bot, chat))
        return
    if context.args:
        raw = context.args[0].strip()
        try:
            target = int(raw)
        except ValueError:
            target = raw
        try:
            info = context.bot.get_chat(target)
        except Exception:
            send_text(context.bot, update.effective_user.id, "Не нашла такой чат. Напиши /setchannel прямо в группе со сборником.")
            return
        send_text(context.bot, update.effective_user.id, _bind_access_chat(context.bot, info))
        return
    chat_id = db.get_setting("access_chat_id")
    title = db.get_setting("access_chat_title")
    if chat_id:
        send_text(
            context.bot,
            update.effective_user.id,
            "Сейчас привязано:\n{}\nID: {}\n\nЧтобы сменить — напиши /setchannel в нужной группе.".format(
                title or "без названия", chat_id
            ),
        )
        return
    send_text(
        context.bot,
        update.effective_user.id,
        "Чат ещё не привязан, потому что /channel в личке не видит группы.\n\n"
        "Открой группу или закрытый канал со сборником и напиши там:\n"
        "/setchannel\n\n"
        "Бот должен быть админом с правом приглашать пользователей.",
    )


def on_my_chat_member(update, context):
    upd = update.my_chat_member
    if not upd or not upd.chat:
        return
    chat = upd.chat
    if chat.type not in ("channel", "supergroup", "group"):
        return
    new = upd.new_chat_member
    if not new or new.status not in ("administrator", "creator"):
        return
    text = _bind_access_chat(context.bot, chat)
    log.info("Access chat set to %s (%s)", chat.title, chat.id)
    for admin_id in ADMIN_IDS:
        send_text(context.bot, admin_id, text)


def cmd_drip(update, context):
    if not is_admin(update.effective_user.id):
        return
    from bot.drip import send_step

    if not context.args or not context.args[0].isdigit():
        send_text(
            context.bot,
            update.effective_user.id,
            "Формат: /drip 1 … /drip 14",
        )
        return
    step = int(context.args[0])
    if step < 1 or step > 14:
        send_text(context.bot, update.effective_user.id, "Номер шага от 1 до 14.")
        return
    send_step(context.bot, update.effective_user.id, step, labeled=False)

