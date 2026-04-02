"""
BTC & XAUT Daily Report Bot
-----------------------------
Каждый день в 10:00 (МСК) отправляет отчёт по BTC и XAUT:
  - Текущая цена
  - Изменение за день и за неделю
  - Прогнозы: краткосрочный / среднесрочный / долгосрочный

Хостинг: Railway
Переменные окружения (задать в Railway):
  TELEGRAM_TOKEN     — токен бота от @BotFather
  ANTHROPIC_API_KEY  — ключ Anthropic
  CHAT_ID            — твой Telegram chat_id (получить через @userinfobot)
"""

import os
import asyncio
import logging
from datetime import time

import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ── Логирование ───────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Конфиг ────────────────────────────────────────────────────────────────────

TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CHAT_ID           = int(os.environ["CHAT_ID"])

# 10:00 МСК = 07:00 UTC
DAILY_HOUR   = 7
DAILY_MINUTE = 0

# ── Клиент Anthropic ──────────────────────────────────────────────────────────

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Промпт ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Ты — автономный финансовый агент-аналитик. Твоя задача — самостоятельно исследовать рынок и составить умный отчёт по BTC и XAUT.

## ШАГ 1: БАЗОВЫЙ СБОР ДАННЫХ
Сначала сделай обязательные поиски:
- "Bitcoin price today" — цена BTC, изменение за 24ч и 7 дней
- "Bitcoin fear greed index today" — индекс страха/жадности (alternative.me)
- "XAUT Tether Gold price today" — цена XAUT, изменение за 24ч и 7 дней

## ШАГ 2: ОЦЕНКА СИТУАЦИИ
После базового сбора САМОСТОЯТЕЛЬНО оцени ситуацию и реши что делать дальше:

🔴 ТРЕВОЖНАЯ СИТУАЦИЯ (любое из условий):
- Изменение BTC за 24ч > 5% или < -5%
- Индекс страха < 20 (экстремальный страх) или > 80 (экстремальная жадность)
- Изменение XAUT за неделю > 8% или < -8%
→ Действие: сделай 3-4 дополнительных поиска чтобы найти ПРИЧИНУ. Ищи новости, события, on-chain данные. Формат отчёта — РАСШИРЕННЫЙ с предупреждением.

🟡 НЕОБЫЧНАЯ СИТУАЦИЯ (данные из разных источников противоречат друг другу):
→ Действие: сделай 2 дополнительных поиска для уточнения. Укажи в отчёте что данные расходятся.

🟢 СПОКОЙНАЯ СИТУАЦИЯ (нет аномалий):
→ Действие: добавь 1-2 поиска по техническому анализу и макро-контексту. Формат — стандартный.

## ШАГ 3: СОСТАВЬ ОТЧЁТ

Для СПОКОЙНОЙ ситуации используй этот формат:

📊 *ОТЧЁТ BTC & XAUT* — [дата]
_Режим: стандартный_

━━━━━━━━━━━━━━━━━━━━
₿ *BITCOIN (BTC)*
━━━━━━━━━━━━━━━━━━━━
💰 Цена: $XX,XXX ([+/-]X.X% за 24ч)
📆 За неделю: [+/-]X.X%
😨 Индекс страха/жадности: XX — [уровень]

📊 *Ключевые уровни:*
Поддержка: $XX,XXX / $XX,XXX / $XX,XXX
Сопротивление: $XX,XXX / $XX,XXX / $XX,XXX

💡 *Анализ:* [2-3 предложения. Что сейчас происходит, вероятный сценарий на ближайшие дни, на что обратить внимание.]

━━━━━━━━━━━━━━━━━━━━
🥇 *TETHER GOLD (XAUT)*
━━━━━━━━━━━━━━━━━━━━
💰 Цена: $X,XXX ([+/-]X.X% за 24ч)
📆 За неделю: [+/-]X.X%

📊 *Ключевые уровни:*
Поддержка: $X,XXX / $X,XXX
Сопротивление: $X,XXX / $X,XXX

💡 *Анализ:* [2-3 предложения. Макро-контекст, драйверы цены, прогноз.]

━━━━━━━━━━━━━━━━━━━━
📌 *Источники:* [2-3 источника]

---

Для ТРЕВОЖНОЙ ситуации используй расширенный формат — добавь в начало:

⚠️ *ВНИМАНИЕ: [кратко опиши аномалию]*

И расширь блок анализа до 4-5 предложений с объяснением причины аномалии и конкретными сценариями развития событий.

---

## ПРАВИЛА АГЕНТА:
- Все цифры — только реальные из поиска, никогда не выдумывай
- Если данные из двух источников расходятся более чем на 2% — ищи третий источник
- Уровни поддержки/сопротивления бери из технического анализа, не придумывай
- Анализ — связный текст, не набор цитат из разных сайтов
- Не противоречь сам себе
- Пиши на русском языке
- Будь конкретным: "BTC тестирует уровень $71,000 третий день подряд" лучше чем "BTC может вырасти"
"""

# ── Генерация отчёта ──────────────────────────────────────────────────────────

def generate_report() -> str:
    """Запускает Claude с web_search и возвращает готовый отчёт."""
    messages = [{
        "role": "user",
        "content": "Составь ежедневный отчёт по BTC и XAUT по заданному формату. Используй актуальные данные из интернета."
    }]

    while True:
        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )

        tool_uses  = [b for b in response.content if b.type == "tool_use"]
        text_parts = [b.text for b in response.content if b.type == "text"]

        if response.stop_reason == "end_turn" or not tool_uses:
            return "\n".join(text_parts) or "❌ Не удалось составить отчёт."

        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": t.id, "content": "Результаты поиска получены."}
                for t in tool_uses
            ]
        })


# ── Отправка отчёта ───────────────────────────────────────────────────────────

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Генерирую ежедневный отчёт BTC/XAUT...")

    # Уведомляем что начали
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="⏳ Собираю данные по BTC и XAUT...",
    )

    try:
        report = await asyncio.get_event_loop().run_in_executor(None, generate_report)
        logger.info("Отчёт готов, отправляю.")

        # Разбиваем если длиннее 4096 символов
        for i in range(0, len(report), 4096):
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=report[i:i+4096],
                parse_mode="Markdown",
            )

    except Exception as e:
        logger.error(f"Ошибка генерации отчёта: {e}")
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=f"❌ Ошибка при составлении отчёта:\n{e}",
        )


# ── Команды ───────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет! Я отслеживаю BTC и XAUT.\n\n"
        "📊 Каждый день в 10:00 МСК ты получаешь отчёт автоматически.\n\n"
        "Команды:\n"
        "/report — получить отчёт прямо сейчас"
    )

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status = await update.message.reply_text("⏳ Собираю данные по BTC и XAUT... (10-30 сек)")
    try:
        report = await asyncio.get_event_loop().run_in_executor(None, generate_report)
        await status.delete()
        for i in range(0, len(report), 4096):
            await update.message.reply_text(report[i:i+4096], parse_mode="Markdown")
    except Exception as e:
        await status.edit_text(f"❌ Ошибка:\n{e}")


# ── Запуск ────────────────────────────────────────────────────────────────────

def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("report", cmd_report))

    # Планировщик: каждый день в 07:00 UTC (= 10:00 МСК)
    app.job_queue.run_daily(
        send_daily_report,
        time=time(hour=DAILY_HOUR, minute=DAILY_MINUTE),
        name="daily_report",
    )

    logger.info(f"🤖 Бот запущен. Отчёт каждый день в {DAILY_HOUR:02d}:{DAILY_MINUTE:02d} UTC (10:00 МСК).")
    app.run_polling()


if __name__ == "__main__":
    main()
