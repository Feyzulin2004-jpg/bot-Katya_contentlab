# AI Content Kit — Telegram-бот

Воронка по ТЗ: бесплатный промт → второй промт → сегментация → доказательства → оффер 999 ₽ → доступ в закрытый канал.

## Ссылки с рилсов

В BotFather ничего дополнительно настраивать не нужно. В сторис/рилс ставь:

- рилс про прайс: `https://t.me/USERNAME_BOTA?start=price`
- рилс про сборник: `https://t.me/USERNAME_BOTA?start=kit`
- рилс про сторис: `https://t.me/USERNAME_BOTA?start=stories`
- рилс про карусель: `https://t.me/USERNAME_BOTA?start=carousel`

Для сборника сработают и `?start=sbornik`, и `?start=collection`.

Бот ставит тег источника (`source_price` / `source_kit` / `source_stories` / `source_carousel`) и сразу открывает нужный первый экран: с прайса — промт для прайса, с карусели — промт для дизайна карусели, со сборника — состав канала и покупка.

## Запуск на Windows

1. Создай бота в [@BotFather](https://t.me/BotFather), скопируй токен.
2. Скопируй `.env.example` в `.env` и заполни:

```
BOT_TOKEN=...
ADMIN_IDS=твой_telegram_id
CHANNEL_INVITE_LINK=https://t.me/+...
PAYMENT_URL=ссылка_на_оплату
PRICE_RUB=999
BOT_USERNAME=username_бота
```

Свой id можно узнать, написав боту `/id`.

3. В командной строке:

```
cd "C:\Users\Алексей\OneDrive\Desktop\Катин бот"
python -m pip install -r requirements.txt
python run.py
```

## Оплата

Сейчас два варианта:

- **Ссылка** — заполни `PAYMENT_URL` (ЮKassa, прокладка, Boosty и т.д.). После оплаты доступ выдаётся командой `/grant telegram_id` из админского аккаунта.
- **Счёт в Telegram** — токен провайдера из BotFather (`PROVIDER_TOKEN`). После успешной оплаты ссылка на канал уходит автоматически.

## Админ-команды

- `/stats` — сколько людей, источники, сегменты, теги
- `/grant 123456789` — выдать доступ и остановить воронку
- `/drip 1` … `/drip 14` — показать себе шаг суточной докрутки
- `/id` — показать свой Telegram ID

## Теги (как в ТЗ)

`source_price`, `source_kit`, `source_stories`, `source_carousel`, `free_price`, `free_stories`, `free_carousel`, `segment_smm`, `segment_business`, `segment_master`, `segment_blog`, `viewed_product`, `clicked_payment`, `paid`, `access_sent`

После `paid` все отложенные продажи этому человеку отключаются.

## Отложенные сообщения

Хранятся в `data/bot.db`, переживают перезапуск бота.

Короткие касания после бесплатного промта: ~15 мин, ~25 мин, ~10 ч.

**Суточная докрутка (если молчит и не жмёт кнопки):** 14 сообщений с интервалом 24 часа. Любое нажатие сдвигает следующее сообщение на 24 часа вперёд. После оплаты цепочка останавливается.

Также: 3 часа и 24 часа после клика «Оплатить», если не купил.

## Медиа и промты

Смотри `media/README.md`. Пока файлов нет, бот шлёт тексты без картинок и не падает.

Постоянное меню: бесплатный промт / что внутри / купить / задать вопрос. Вопросы пересылаются в `ADMIN_IDS`.
