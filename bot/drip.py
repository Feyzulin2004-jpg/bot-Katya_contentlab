# -*- coding: utf-8 -*-
"""Суточная докрутка: 14 сообщений, если человек молчит."""
import logging

from bot import db, texts
from bot import keyboards as kb
from bot import media as md
from bot.config import DELAY_DRIP, DRIP_TOTAL

log = logging.getLogger(__name__)

DAY_TITLES = {
    1: "Сообщение первого дня:",
    2: "Сообщение второго дня:",
    3: "Сообщение третьего дня:",
    4: "Сообщение четвёртого дня:",
    5: "Сообщение пятого дня:",
    6: "Сообщение шестого дня:",
    7: "Сообщение седьмого дня:",
    8: "Сообщение восьмого дня:",
    9: "Сообщение девятого дня:",
    10: "Сообщение десятого дня:",
    11: "Сообщение одиннадцатого дня:",
    12: "Сообщение двенадцатого дня:",
    13: "Сообщение тринадцатого дня:",
    14: "Сообщение четырнадцатого дня:",
}

DRIP_MEDIA = {
    1: ["IMG_8433"],
    2: ["IMG_8431"],
    3: ["IMG_8398"],
    4: ["IMG_8437"],
    5: ["IMG_8443", "IMG_8281", "IMG_7713", "IMG_7566"],
    6: ["IMG_8445"],
    7: [],
    8: ["IMG_8422"],
    9: ["IMG_8431"],
    10: ["IMG_0047", "IMG_8580", "IMG_8581"],
    11: ["IMG_8422"],
    12: ["IMG_8585"],
    13: ["IMG_8587"],
    14: ["IMG_8422"],
}


def step_text(step):
    mapping = {
        1: texts.DRIP_1,
        2: texts.DRIP_2,
        3: texts.DRIP_3,
        4: texts.DRIP_4,
        5: texts.DRIP_5,
        6: texts.DRIP_6,
        7: texts.DRIP_7,
        8: texts.DRIP_8,
        9: texts.DRIP_9,
        10: texts.DRIP_10,
        11: texts.DRIP_11,
        12: texts.DRIP_12,
        13: texts.DRIP_13,
        14: texts.DRIP_14,
    }
    return mapping.get(step)


def send_step(bot, user_id, step, labeled=False):
    text = step_text(step)
    if not text:
        return False
    if labeled:
        bot.send_message(user_id, DAY_TITLES[step])
    md.send_named_many(
        bot,
        user_id,
        DRIP_MEDIA.get(step) or [],
        caption=text,
        reply_markup=kb.drip(step),
    )
    return True


def arm_silence_drip(user_id):
    user = db.get_user(user_id)
    if not user or user["paid"] or user["blocked"]:
        db.cancel_user_jobs(user_id, ["drip"])
        return
    if int(user.get("drip_step") or 0) >= DRIP_TOTAL:
        db.cancel_user_jobs(user_id, ["drip"])
        return
    db.schedule_job(user_id, "drip", DELAY_DRIP)


def process_due_drip(bot, user_id):
    user = db.get_user(user_id)
    if not user or user["paid"] or user["blocked"]:
        return
    step = int(user.get("drip_step") or 0) + 1
    if step > DRIP_TOTAL:
        return
    send_step(bot, user_id, step)
    db.set_fields(user_id, drip_step=step)
    if step < DRIP_TOTAL:
        db.schedule_job(user_id, "drip", DELAY_DRIP)


def handle_button(bot, user_id, action):
    from bot.funnel import send_text

    if action == "show1":
        md.send_named(
            bot,
            user_id,
            "IMG_8422",
            caption=texts.DRIP_1_SHOW,
            reply_markup=kb.buy(),
        )
        return "ok"
    if action == "visual":
        return "visual"
    if action == "text":
        md.send_named(bot, user_id, "IMG_8445", caption=texts.DRIP_6_SHOW, reply_markup=kb.buy())
        return "ok"
    if action == "bonus":
        send_text(bot, user_id, texts.DRIP_7_BONUS, reply_markup=kb.buy())
        return "ok"
    return "catalog"
