# Reward Telegram Bot

Модульний Telegram reward-бот на Python 3.12+, aiogram 3.x, SQLAlchemy 2.x, PostgreSQL/SQLite, FastAPI та Uvicorn.

## Можливості

- Обов'язкова підписка на основний канал перед доступом.
- 1 безкоштовний стартовий спін після першої успішної перевірки.
- 7 призів: 10 / 20 / 30 / 50 / 100 / 200 / 300 грн.
- Сервер визначає результат спіну до Telegram-анімації.
- Реферальна система через `?start=ref_USER_ID`.
- +1 спін за кожні 3 унікальні реферали.
- Завдання з адмін-панелі: підписка, перегляд каналу, посилання, інше.
- Для "перегляду каналу" не симулюється перевірка факту читання; бот перевіряє доступний Telegram-сигнал — членство у відповідному публічному каналі.
- Для інших завдань є режим ручної перевірки.
- Баланс, історія, виплати, резерв коштів та повернення при відхиленні.
- Захист від дублювання завдань, рефералів, спінів і виплат.
- Адмін-панель: статистика, користувачі, баланси, спіни, гривневі нарахування, завдання, перевірки, розсилка, виплати, шанси, канали, способи виплати, налаштування та логи.
- PostgreSQL у production, SQLite локально.
- FastAPI health endpoint `/` -> `{"status":"ok"}`.
- Запуск через `python bot.py`.

## Локальний запуск

1. Потрібен Python 3.12+.
2. Створи `.env` на основі `.env.example`.
3. Заповни `BOT_TOKEN` і `ADMIN_IDS`.
4. Встанови залежності:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

5. Запусти:

```bash
python bot.py
```

Без `DATABASE_URL` використовується SQLite-файл `data/reward_bot.db`.

## Налаштування каналу

Після першого запуску відкрий адмін-панель -> **📢 Канали** та задай:

- username основного каналу, наприклад `ua_2024k`;
- Chat ID каналу, наприклад `-100...`.

Щоб `get_chat_member` міг перевіряти підписку в каналі, бот має бути доданий до каналу з правами адміністратора.

## Render

`render.yaml` створює web service і PostgreSQL. Render сам передає `DATABASE_URL`.

Потрібно задати secrets:

- `BOT_TOKEN`
- `ADMIN_IDS`

Команда запуску вже задана як:

```bash
python bot.py
```

FastAPI слухає `0.0.0.0:$PORT`, а Telegram працює через long polling.

## Безпека

Критичні фінансові операції використовують SQLAlchemy `SELECT ... FOR UPDATE` / транзакційні зміни. Спін списується та виграш зараховується в одній транзакції. Для виплати кошти резервуються при створенні заявки; при відхиленні повертаються атомарно. Подвійна обробка статусної заявки не дозволяється.

## Структура

```text
reward_bot_project/
├── bot.py
├── requirements.txt
├── .env.example
├── render.yaml
├── README.md
├── database/
│   ├── db.py
│   ├── models.py
│   └── seed.py
├── handlers/
│   ├── start.py
│   ├── user.py
│   ├── admin.py
│   └── admin_extra.py
├── keyboards/
│   ├── common.py
│   ├── tasks.py
│   ├── withdraw.py
│   └── admin.py
├── middlewares/
│   ├── db.py
│   └── throttling.py
├── services/
│   ├── users.py
│   ├── rewards.py
│   ├── tasks.py
│   ├── withdrawals.py
│   ├── history.py
│   ├── stats.py
│   ├── settings.py
│   └── admin.py
└── utils/
    ├── config.py
    ├── formatting.py
    ├── security.py
    ├── states.py
    └── texts.py
```

> Render Free PostgreSQL станом на жовтень 2026 року має 1 GB та термін 30 днів; для постійного production сховища використовуйте платний план.
