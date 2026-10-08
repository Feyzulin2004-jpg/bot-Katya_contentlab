# -*- coding: utf-8 -*-
import json
import logging
import time

from telegram.error import BadRequest, TimedOut, Unauthorized

from bot import db, texts
from bot.config import ACCESS_CHAT, CHANNEL_INVITE_LINK
from bot import keyboards as kb
from bot import media as md
from bot import tags as T

log = logging.getLogger(__name__)


def safe_send(bot, user_id, method, *args, **kwargs):
    try:
        return getattr(bot, method)(user_id, *args, **kwargs)
    except Unauthorized:
        db.mark_blocked(user_id, True)
        log.info("User %s blocked the bot", user_id)
        return None
    except TimedOut:
        log.warning("Timeout sending to %s", user_id)
        return None
    except BadRequest as exc:
        log.warning("BadRequest to %s: %s", user_id, exc)
        return None
    except Exception:
        log.exception("Send failed to %s", user_id)
        return None


def send_text(bot, user_id, text, reply_markup=None, parse_mode=None):
    chunks = _chunks(text)
    result = None
    for i, chunk in enumerate(chunks):
        markup = reply_markup if i == len(chunks) - 1 else None
        result = safe_send(
            bot,
            user_id,
            "send_message",
            chunk,
            reply_markup=markup,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
    return result


def _chunks(text, size=3900):
    text = text or ""
    if len(text) <= size:
        return [text]
    parts = []
    while text:
        parts.append(text[:size])
        text = text[size:]
    return parts


def send_asset(bot, user_id, stem, caption=None, reply_markup=None):
    try:
        return md.send_named(bot, user_id, stem, caption=caption, reply_markup=reply_markup)
    except Exception:
        log.exception("Не удалось отправить %s", stem)
        return False


def send_media_folder(bot, user_id, folder, caption=None):
    files = md.album(folder)
    if not files:
        return False
    try:
        return md.send_photos(bot, user_id, files, caption=caption)
    except Exception:
        log.exception("Media send failed")
        return False


def prompt_text(kind):
    name = {"price": "price", "stories": "stories", "carousel": "carousel"}.get(kind, "stories")
    body = md.read_text("prompts", "{}.txt".format(name))
    if body:
        return body
    return texts.PROMPT_PLACEHOLDER.format(name=name)


def _remaining_free(user_id, exclude=None):
    left = []
    for kind, tag in T.FREE_BY_KIND.items():
        if kind == exclude:
            continue
        if not db.has_tag(user_id, tag):
            left.append(kind)
    return left


def give_prompt(bot, user_id, kind):
    user = db.get_user(user_id)
    if not user:
        return
    intro = texts.CAROUSEL_HOWTO if kind == "carousel" else texts.PROMPT_INTRO
    send_text(bot, user_id, intro, reply_markup=kb.main_reply(user_id))
    try:
        md.send_prompt_video(bot, user_id, kind)
    except Exception:
        log.exception("Не удалось отправить видео промта")
    try:
        sent_doc = md.send_prompt_doc(bot, user_id, kind)
    except Exception:
        log.exception("Не удалось отправить документ промта")
        sent_doc = False
    if not sent_doc:
        send_text(bot, user_id, prompt_text(kind))
    send_text(
        bot,
        user_id,
        "Сохрани промт и попробуй на своём проекте.",
        reply_markup=kb.after_prompt(_remaining_free(user_id, exclude=kind)),
    )
    tag = T.FREE_BY_KIND.get(kind)
    if tag:
        db.add_tag(user_id, tag)
    if not _remaining_free(user_id):
        db.cancel_user_jobs(user_id, ["second_nudge"])
    user = db.get_user(user_id)
    if user and not user.get("segment"):
        send_text(bot, user_id, texts.SEGMENT_ASK, reply_markup=kb.segment())
    if not db.has_tag(user_id, "funnel_started"):
        db.add_tag(user_id, "funnel_started")
        start_passive_funnel(user_id)


def start_passive_funnel(user_id):
    from bot.config import DELAY_HOOK, DELAY_SECOND_PROMPT_NUDGE, DELAY_WARMUP, DELAY_WHY_COLLECTION

    db.schedule_job(user_id, "warmup", DELAY_WARMUP)
    db.schedule_job(user_id, "second_nudge", DELAY_SECOND_PROMPT_NUDGE)
    db.schedule_job(user_id, "why_collection", DELAY_WHY_COLLECTION)
    db.schedule_job(user_id, "hook_teaser", DELAY_HOOK)


def access_chat_id():
    saved = db.get_setting("access_chat_id")
    if saved:
        try:
            return int(saved)
        except ValueError:
            return saved
    return ACCESS_CHAT or None


def grant_access(bot, user_id):
    user = db.get_user(user_id)
    already = bool(user and user.get("paid") and db.has_tag(user_id, T.ACCESS_SENT))
    if already:
        return
    db.mark_paid(user_id)
    db.add_tag(user_id, T.ACCESS_SENT)
    link = make_access_link(bot, user_id)
    if link:
        send_text(
            bot,
            user_id,
            texts.PAID_OK.format(name="AI Content Kit", link=link),
            reply_markup=kb.channel(link),
        )
        return
    send_text(
        bot,
        user_id,
        "Оплата прошла ✅\nДоступ в канал выдадим вручную в ближайшее время. Если долго нет ссылки — напиши в поддержку.",
        reply_markup=kb.main_reply(user_id),
    )
    from bot.config import ADMIN_IDS

    for admin_id in ADMIN_IDS:
        send_text(
            bot,
            admin_id,
            "Оплата прошла, но приглашение в канал не создалось. User id: {}. Добавь бота админом в закрытый канал.".format(
                user_id
            ),
        )


def make_access_link(bot, user_id):
    chat = access_chat_id()
    if not chat:
        return CHANNEL_INVITE_LINK if CHANNEL_INVITE_LINK.startswith("http") and "+xxxxx" not in CHANNEL_INVITE_LINK and "Katya_contentlab" not in CHANNEL_INVITE_LINK else ""
    try:
        invite = bot.create_chat_invite_link(
            chat_id=chat,
            expire_date=int(time.time()) + 7 * 24 * 3600,
            member_limit=1,
        )
        return invite.invite_link
    except Exception:
        log.exception("Не удалось создать приглашение в %s", chat)
        return ""


def send_example_follow(bot, user_id, payload):
    try:
        index = int(payload or 0)
    except ValueError:
        index = 0
    steps = texts.EXAMPLE_FOLLOW
    if index < 0 or index >= len(steps):
        return
    caption, stems = steps[index]
    md.send_stems(bot, user_id, stems, caption=caption)
    if index + 1 < len(steps):
        db.schedule_job(user_id, "examples_more", 2 * 60, payload=str(index + 1))


def run_job(bot, job):
    user_id = job["user_id"]
    user = db.get_user(user_id)
    if not user or user["blocked"]:
        return
    kind = job["kind"]
    if user["paid"] and kind not in ("examples_outro", "examples_prompt", "examples_more"):
        return
    if kind == "warmup":
        if db.has_tag(user_id, T.VIEWED_PRODUCT) or user.get("segment"):
            return
        send_text(bot, user_id, texts.WARMUP, reply_markup=kb.warmup())
    elif kind == "second_nudge":
        if not _remaining_free(user_id):
            return
        send_text(bot, user_id, texts.NUDGE_SECOND, reply_markup=kb.second_nudge())
    elif kind == "why_collection":
        send_asset(bot, user_id, "IMG_8422")
        send_text(bot, user_id, texts.NUDGE_WHY, reply_markup=kb.look_collection())
    elif kind == "hook_teaser":
        md.send_named(
            bot,
            user_id,
            "IMG_8427",
            caption=texts.HOOK_TEASER,
            reply_markup=kb.offer(),
        )
    elif kind == "drip":
        from bot.drip import process_due_drip

        process_due_drip(bot, user_id)
    elif kind == "checkout_1":
        if db.has_tag(user_id, T.PAID):
            return
        send_checkout_reminder(bot, user_id, texts.CHECKOUT_REMINDER_1)
    elif kind == "checkout_2":
        if db.has_tag(user_id, T.PAID):
            return
        send_checkout_reminder(bot, user_id, texts.CHECKOUT_REMINDER_2)
    elif kind in ("examples_plan", "examples_outro", "examples_prompt"):
        return
    elif kind == "examples_more":
        send_example_follow(bot, user_id, job.get("payload"))
    elif kind == "checkout_value":
        md.send_named(
            bot,
            user_id,
            "IMG_8423",
            caption=texts.VALUE_EXAMPLE,
            reply_markup=kb.take_all(),
        )
    elif kind == "checkout_pos":
        send_text(bot, user_id, texts.POSITIONING, reply_markup=kb.positioning())
    elif kind == "yookassa_poll":
        poll_yookassa(bot, user_id, job.get("payload"))


def poll_yookassa(bot, user_id, payload):
    from bot import yookassa as yk

    user = db.get_user(user_id)
    if user and user.get("paid"):
        return
    payment_id = payload or ""
    n = 0
    if payload and str(payload).startswith("{"):
        try:
            data = json.loads(payload)
            payment_id = data.get("id") or ""
            n = int(data.get("n") or 0)
        except ValueError:
            pass
    try:
        info = yk.get_payment(payment_id)
    except Exception:
        log.exception("Не удалось проверить оплату")
        if n < 120:
            db.schedule_job(
                user_id,
                "yookassa_poll",
                10,
                json.dumps({"id": payment_id, "n": n + 1}),
            )
        return
    status = info.get("status")
    if status == "succeeded":
        grant_access(bot, user_id)
        return
    if status in ("canceled", "cancelled"):
        send_text(bot, user_id, "Оплата отменена. Если захочешь — нажми «Оплатить» ещё раз.")
        return
    if n < 120:
        db.schedule_job(
            user_id,
            "yookassa_poll",
            10,
            json.dumps({"id": payment_id, "n": n + 1}),
        )


def send_checkout_reminder(bot, user_id, preface):
    send_text(bot, user_id, preface, reply_markup=kb.checkout())


def start_yookassa_pay(bot, user_id):
    from bot import config
    from bot import yookassa as yk

    if not yk.configured():
        return False
    if not config.BOT_USERNAME:
        try:
            me = bot.get_me()
            if me and me.username:
                config.BOT_USERNAME = me.username
        except Exception:
            pass
    try:
        payment_id, url, status = yk.create_payment(user_id)
    except Exception:
        log.exception("Не удалось создать платёж ЮKassa")
        send_text(bot, user_id, "Сейчас ссылка на оплату не открылась. Нажми «Оплатить» ещё раз через минуту.")
        return True
    if status == "succeeded":
        grant_access(bot, user_id)
        return True
    if not payment_id or not url:
        send_text(bot, user_id, "Не получилось создать ссылку на оплату. Напиши в поддержку.")
        return True
    db.set_fields(user_id, last_payment_id=payment_id)
    db.schedule_job(
        user_id,
        "yookassa_poll",
        8,
        json.dumps({"id": payment_id, "n": 0}),
    )
    send_text(
        bot,
        user_id,
        texts.PAY_LINK.format(price="{} ₽".format(config.PRICE_RUB), url=url),
    )
    return True


def catch_pending_payment(bot, user_id):
    from bot import yookassa as yk

    user = db.get_user(user_id)
    if not user or user.get("paid") or not user.get("last_payment_id"):
        return
    if not yk.configured():
        return
    try:
        info = yk.get_payment(user.get("last_payment_id"))
    except Exception:
        return
    if info.get("status") == "succeeded":
        grant_access(bot, user_id)


def process_due(bot):
    for job in db.due_jobs():
        try:
            run_job(bot, job)
            db.finish_job(job["id"], "done")
        except Exception:
            log.exception("Job %s failed", job["id"])
            db.finish_job(job["id"], "error")
        time.sleep(0.05)
