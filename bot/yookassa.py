# -*- coding: utf-8 -*-
import base64
import json
import logging
import uuid

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bot import config

log = logging.getLogger(__name__)
API = "https://api.yookassa.ru/v3/payments"


def configured():
    return bool(config.YOOKASSA_SHOP_ID and config.YOOKASSA_SECRET_KEY)


def _headers(idempotence=None):
    token = base64.b64encode(
        "{}:{}".format(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET_KEY).encode("utf-8")
    ).decode("ascii")
    headers = {
        "Authorization": "Basic " + token,
        "Content-Type": "application/json",
    }
    if idempotence:
        headers["Idempotence-Key"] = idempotence
    return headers


def _request(method, url, body=None, idempotence=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(url, data=data, headers=_headers(idempotence), method=method)
    try:
        resp = urlopen(req, timeout=30)
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}
    except HTTPError as exc:
        err = exc.read().decode("utf-8", "replace")
        log.warning("YooKassa HTTP %s: %s", exc.code, err[:500])
        raise
    except URLError:
        log.exception("YooKassa network error")
        raise


def create_payment(user_id):
    amount = "{:.2f}".format(float(config.PRICE_RUB))
    return_url = "https://t.me/{}".format(config.BOT_USERNAME) if config.BOT_USERNAME else "https://t.me"
    body = {
        "amount": {"value": amount, "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": "{} · Telegram {}".format(config.PRODUCT_NAME, user_id),
        "metadata": {"user_id": str(user_id)},
    }
    if config.YOOKASSA_RECEIPT_EMAIL:
        body["receipt"] = {
            "customer": {"email": config.YOOKASSA_RECEIPT_EMAIL},
            "items": [
                {
                    "description": config.PRODUCT_NAME[:128],
                    "quantity": "1.00",
                    "amount": {"value": amount, "currency": "RUB"},
                    "vat_code": 1,
                    "payment_mode": "full_payment",
                    "payment_subject": "service",
                }
            ],
        }
    data = _request("POST", API, body, idempotence=str(uuid.uuid4()))
    confirmation = (data.get("confirmation") or {}).get("confirmation_url")
    return data.get("id"), confirmation, data.get("status")


def get_payment(payment_id):
    if not payment_id:
        return {}
    return _request("GET", API + "/" + payment_id)
