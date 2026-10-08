# -*- coding: utf-8 -*-
"""Единый набор тегов воронки."""

SOURCE_PRICE = "source_price"
SOURCE_STORIES = "source_stories"
SOURCE_CAROUSEL = "source_carousel"
SOURCE_KIT = "source_kit"
FREE_PRICE = "free_price"
FREE_STORIES = "free_stories"
FREE_CAROUSEL = "free_carousel"
SEGMENT_SMM = "segment_smm"
SEGMENT_BUSINESS = "segment_business"
SEGMENT_MASTER = "segment_master"
SEGMENT_BLOG = "segment_blog"
VIEWED_PRODUCT = "viewed_product"
CLICKED_PAYMENT = "clicked_payment"
PAID = "paid"
ACCESS_SENT = "access_sent"

SEGMENT_MAP = {
    "smm": SEGMENT_SMM,
    "business": SEGMENT_BUSINESS,
    "master": SEGMENT_MASTER,
    "blog": SEGMENT_BLOG,
}

FREE_BY_KIND = {
    "price": FREE_PRICE,
    "stories": FREE_STORIES,
    "carousel": FREE_CAROUSEL,
}

START_PAYLOADS = {
    "price": SOURCE_PRICE,
    "promt_price": SOURCE_PRICE,
    "prompt_price": SOURCE_PRICE,
    "prajs": SOURCE_PRICE,
    "prays": SOURCE_PRICE,
    "stories": SOURCE_STORIES,
    "story": SOURCE_STORIES,
    "promt_stories": SOURCE_STORIES,
    "prompt_stories": SOURCE_STORIES,
    "carousel": SOURCE_CAROUSEL,
    "karusel": SOURCE_CAROUSEL,
    "promt_carousel": SOURCE_CAROUSEL,
    "prompt_carousel": SOURCE_CAROUSEL,
    "promt": SOURCE_PRICE,
    "kit": SOURCE_KIT,
    "sbornik": SOURCE_KIT,
    "collection": SOURCE_KIT,
    "catalog": SOURCE_KIT,
}

FUNNEL_JOBS = (
    "warmup",
    "second_nudge",
    "why_collection",
    "drip",
    "checkout_1",
    "checkout_2",
)
